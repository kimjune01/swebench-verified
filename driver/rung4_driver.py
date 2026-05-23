#!/usr/bin/env python3
"""Rung 4 driver — single-diagnostician recon + outer loop. Grading is the official eval.py.

Per instance (model runs LOCALLY; SUT is an offline container on the box):
  pull -> run -> git apply test_patch -> COMMIT it -> warm online (caches deps,
  captures FAIL-ON-BASE) -> cut net -> OUTER LOOP:

    recon  : ONE Sonnet diagnosis -> structured handoff. The adversary is the gate
             + the outer loop (iteration), not a parallel blind.
    craft  : Sonnet generates the patch, a LOCAL codex subagent challenges it (volley),
             the gate arbitrates. gate loop (<=8), live in container.
    audit  : full gate, classify regressions vs the captured fail-on-base, emit
             VERDICT + RE-ENTER route. NO git stash (the base capture is the baseline).

CONTAMINATION NOTE: craft uses codex (GPT-5.5, recent cutoff). This is a LEADERBOARD /
spectacle configuration, NOT a contamination-clean run — codex's cutoff postdates the
instances. For the clean-science track (post-cutoff firewall), drop the codex volley and
run craft single-model. codex runs on the plan machine; only the container is offline.

  If audit != RESOLVED and depth < MAX_OUTER:
    RE-ENTER: recon  -> re-diagnose (kill report = new H0; recon re-runs)
    RE-ENTER: craft  -> narrow the over-broad fix (recon was right; skip re-diagnose)
  Fixed-point halt: recon reports re-diagnosis converged on the prior root cause.

  Capture model_patch = `git diff HEAD` regardless of verdict -> teardown.

Hypothesis graph accumulates per instance at r4_hgraph_<iid>.md (crash checkpoint).

Usage: rung4_driver.py <box_env_file> <round_tasks.json> <instance_id> [...]
"""
import json, subprocess, sys, time, pathlib, os, re

HERE = pathlib.Path("/tmp/swebench-abduction")
MAX_OUTER = 3

# Skills are repo-local (hardlinked to the canonical copies). Resolve relative to
# this file so the repo is self-contained for anyone who clones it.
_SKILLS = pathlib.Path(__file__).resolve().parent.parent / "skills"
RECON_SKILL = (_SKILLS / "recon/skill.md").read_text()
CRAFT_SKILL = (_SKILLS / "craft/skill.md").read_text()
AUDIT_SKILL = (_SKILLS / "audit/skill.md").read_text()

# Model = Claude Sonnet by default; override with RCA_MODEL for any model your
# `claude` CLI / API key can reach.
MODEL = os.environ.get("RCA_MODEL", "claude-sonnet-4-5")

def plan_env():
    """Auth-mode agnostic. Default: pass the environment through, so an
    ANTHROPIC_API_KEY (API access) is honored and, if absent, the `claude` CLI
    falls back to its logged-in subscription session. Set CLAUDE_SUBSCRIPTION=1
    to force the subscription path by dropping the API key (useful when you have
    a key in your shell but want to bill a Max/Pro plan instead). codex uses its
    own auth (ChatGPT login or OPENAI_API_KEY) untouched."""
    e = os.environ.copy()
    if os.environ.get("CLAUDE_SUBSCRIPTION"):
        e.pop("ANTHROPIC_API_KEY", None)
    return e

BOXENV = dict(l.strip().split("=",1) for l in open(sys.argv[1]) if "=" in l)
TASKS = {d["instance_id"]: d for d in json.load(open(sys.argv[2]))}
# SSH user defaults to ec2-user (AWS AL2023); override with SSH_USER for any host.
SSH_USER = os.environ.get("SSH_USER", BOXENV.get("SSH_USER", "ec2-user"))
PEM = f"/tmp/{BOXENV['KEY']}.pem"; HOST = f"{SSH_USER}@{BOXENV['PUBIP']}"
STEM = pathlib.Path(sys.argv[1]).stem
LEDGER = HERE/f"rung4_results_{STEM}.jsonl"
PATCHES = HERE/f"rung4_patches_{STEM}.jsonl"

def ssh(remote, timeout=600, inp=None):
    return subprocess.run(
        ["ssh","-o","StrictHostKeyChecking=no","-o","ConnectTimeout=10","-i",PEM,HOST,remote],
        capture_output=True, text=True, timeout=timeout, input=inp)

def log(obj):
    with open(LEDGER,"a") as f: f.write(json.dumps(obj)+"\n")
    sys.stderr.write(f"[{obj.get('instance')}] {obj.get('stage')}: {obj.get('msg','')}\n")
    sys.stderr.flush()

def setup(inst):
    iid = inst["instance_id"]; img = inst["image_name"].replace("docker.io/","")
    ssh(f"sudo docker pull {img} 2>&1 | tail -1", timeout=1200)
    cid = ssh(f"sudo docker run -d {img} sleep infinity").stdout.strip()
    if not cid or len(cid) < 12:
        log({"instance":iid,"stage":"setup","msg":f"run failed: {cid[:80]}"}); return None
    root = inst.get("repo_dir") or ssh(f"sudo docker exec {cid} pwd").stdout.strip() or "/"
    # Stage the test patch OUTSIDE the repo (/tmp, not {root}) so `git add -A` can't
    # sweep the scaffolding file into the tree. A committed tp.patch leaks a `delete
    # tp.patch` hunk into the captured prediction, which fails to apply on the official
    # harness's clean base and trips git's -R heuristic (django-15987 false-positive).
    ssh(f"cat > /tmp/tp.patch && sudo docker cp /tmp/tp.patch {cid}:/tmp/tp.patch",
        inp=inst["test_patch"])
    ap = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git apply /tmp/tp.patch && "
             f"git -c user.email=r4@x -c user.name=r4 add -A && "
             f"git -c user.email=r4@x -c user.name=r4 commit -q -m testpatch && "
             f"echo APPLIED $(git rev-parse HEAD)'")
    if "APPLIED" not in ap.stdout:
        log({"instance":iid,"stage":"setup","msg":f"git apply/commit failed: {(ap.stdout+ap.stderr)[:200]}"})
        return (cid, root, False, None)
    tsha = ap.stdout.split("APPLIED")[1].strip().split()[0]
    return (cid, root, True, tsha)

def warm_and_failbase(inst, cid, root):
    """Run the official test_cmd ONCE online: caches deps AND captures fail-on-base.
    The captured output is audit's baseline for 'pre-existing failure'."""
    tc = (inst.get("install_config") or {}).get("test_cmd","")
    if not tc: return ""
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && {pre}{tc} 2>&1 | tail -120'", timeout=1800)
    tag = inst["instance_id"].replace("/","_")
    base = f"$ {tc}\n\n{r.stdout}{r.stderr}"
    (HERE/f"r4_failbase_{tag}.txt").write_text(base)
    return base

def helpers(inst, cid, root):
    iid = inst["instance_id"]; tag = iid.replace("/","_").replace("__","_")
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    box = f"/tmp/box-sh-{tag}"
    s = (f"#!/bin/bash\n"
         f"printf '%s' \"$*\" | ssh -o StrictHostKeyChecking=no -i {PEM} {HOST} "
         f"\"cat >/tmp/_bc_{tag} && sudo docker cp /tmp/_bc_{tag} {cid}:/tmp/_bc >/dev/null && "
         f"sudo docker exec {cid} bash -lc 'cd {root} && {pre}bash /tmp/_bc'\"\n")
    pathlib.Path(box).write_text(s); subprocess.run(["chmod","+x",box])
    tc = (inst.get("install_config") or {}).get("test_cmd","").replace("'","'\\''")
    gate = f"/tmp/gate-{tag}"
    g = (f"#!/bin/bash\n"
         f"ssh -o StrictHostKeyChecking=no -i {PEM} {HOST} "
         f"\"sudo docker exec {cid} bash -lc 'cd {root} && {pre}{tc} 2>&1 | tail -120'\"\n")
    pathlib.Path(gate).write_text(g); subprocess.run(["chmod","+x",gate])
    return box, gate

def claude(prompt_text, cwd, tag, timeout=2400):
    pf = HERE/f"r4_prompt_{tag}.txt"; pf.write_text(prompt_text)
    cwd = pathlib.Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    p = subprocess.run(
        ["claude","--print","--model","claude-sonnet-4-5",
         "--dangerously-skip-permissions","--disallowedTools","WebSearch,WebFetch,Task"],
        stdin=open(pf), capture_output=True, text=True, timeout=timeout,
        cwd=str(cwd), env=plan_env())
    dt = time.time()-t0
    (HERE/f"r4_out_{tag}.txt").write_text(p.stdout+"\n---STDERR---\n"+p.stderr)
    return p.stdout, dt

# ── recon: single diagnostician (gate + outer loop is the adversary) ──────────

def recon(inst, box, gate, hgraph, kill_report, depth):
    iid = inst["instance_id"]; tag = f"recon_{iid.replace('/','_')}_d{depth}"
    added = "\n".join(l[1:] for l in inst["test_patch"].splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    kr = (f"\nAUDIT KILL REPORT (prior diagnosis failed — treat as new H0; do NOT "
          f"re-propose the killed root cause):\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /recon skill below. Diagnose from the code alone and print "
        f"your handoff to stdout starting `# Recon:`.\n\n"
        f"ENVIRONMENT:\n"
        f"- Code is in an offline container. Run ALL reads via: `{box} '<cmd>'` "
        f"(it already cd's to repo root — do NOT prepend cd). No internet, no gh, no codex.\n"
        f"- Run the failing tests: `{gate}`\n"
        f"- Append hypothesis nodes to: {hgraph} (never truncate).\n"
        f"- Failing tests live in: {testfiles}\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"PROBLEM:\n{inst['problem_statement'][:4000]}\n\n"
        f"ADDED FAILING TESTS:\n{added[:2500]}\n"
        f"{kr}"
        f"\n===================== THE /recon SKILL =====================\n{RECON_SKILL}\n"
    )
    out, dt = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=2000)
    fixed_point = "FIXED POINT" in out.upper()
    log({"instance":iid,"stage":"recon","depth":depth,"wall_s":round(dt),
         "fixed_point":fixed_point})
    return out, fixed_point

# ── craft ─────────────────────────────────────────────────────────────────────

def craft(inst, box, gate, hgraph, handoff, kill_report, depth):
    iid = inst["instance_id"]; tag = f"craft_{iid.replace('/','_')}_d{depth}"
    narrow = (f"\nAUDIT KILL REPORT — a PASS_TO_PASS test regressed. recon was right; "
              f"the fix is too broad. Enter NARROW mode: keep FAIL_TO_PASS passing AND "
              f"restore the regressed test.\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /craft skill below. You generate the patch from the recon "
        f"handoff; codex challenges it; the gate arbitrates.\n\n"
        f"ENVIRONMENT:\n"
        f"- Offline container. Edit/read via: `{box} '<cmd>'` (already at repo root — "
        f"do NOT prepend cd; use sed/python3/patch inside it).\n"
        f"- Verify with the gate: `{gate}` (max 8 iterations).\n"
        f"- `codex` runs LOCALLY (not in the container, so it can't read the repo or run "
        f"the gate). Bridge it: pull file contents via the box helper, paste them into the "
        f"codex prompt. Invoke via stdin heredoc: `cat <<'EOF' | codex exec -` ... `EOF`. "
        f"ALWAYS volley with codex: show it your drafted diff BEFORE the first gate run, "
        f"and show it the gate output + diff on EVERY gate failure before revising. Never "
        f"gate a fix codex hasn't seen. ~6-8 codex calls; it converges in 2-3.\n"
        f"- Append gate-loop nodes to: {hgraph}.\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"RECON HANDOFF (canonical — act on this):\n{handoff[:7000]}\n"
        f"{narrow}\n"
        f"When all FAIL_TO_PASS pass in the gate, print RESOLVED (a green gate ends the "
        f"loop even if codex still has notes). If the diagnosis looks wrong after 3 stuck "
        f"iterations, print `NOT-RESOLVED — re-diagnose`. Only judge from gate output — "
        f"never your reasoning, never codex's approval.\n\n"
        f"===================== THE /craft SKILL =====================\n{CRAFT_SKILL}\n"
    )
    out, dt = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=3600)
    redirect = "re-diagnose" in out.lower()
    claim = ("RESOLVED" in out) and ("NOT-RESOLVED" not in out)
    log({"instance":iid,"stage":"craft","depth":depth,"wall_s":round(dt),
         "claim":claim,"wants_rediagnose":redirect})
    return out, redirect

# ── audit ─────────────────────────────────────────────────────────────────────

def audit(inst, box, gate, hgraph, failbase, depth):
    iid = inst["instance_id"]; tag = f"audit_{iid.replace('/','_')}_d{depth}"
    adapter = (
        f"You will follow the /audit skill below. The craft edits are live in the tree.\n\n"
        f"ENVIRONMENT:\n"
        f"- Offline container. Read via `{box} '<cmd>'` (already at root). NEVER mutate "
        f"the tree (no git stash / apply / edits).\n"
        f"- Full gate: `{gate}`.\n"
        f"- Append breakdown to: {hgraph}.\n\n"
        f"FAIL_TO_PASS: {str(inst['FAIL_TO_PASS'])[:600]}\n"
        f"PASS_TO_PASS: {str((inst.get('PASS_TO_PASS') or []))[:800]}\n\n"
        f"FAIL-ON-BASE CAPTURE (your baseline for pre-existing failures — a test failing "
        f"here was already broken before the patch):\n{failbase[:3500]}\n\n"
        f"End with two lines exactly:\nVERDICT: <RESOLVED|NOT_RESOLVED|PARTIAL>\n"
        f"RE-ENTER: <recon|craft|none>\n\n"
        f"===================== THE /audit SKILL =====================\n{AUDIT_SKILL}\n"
    )
    out, dt = claude(adapter, HERE/f"r4_cwd_{tag}", tag, timeout=1200)
    verdict, route = "UNKNOWN", "none"
    for line in reversed(out.strip().splitlines()):
        l = line.strip()
        m = re.match(r"VERDICT:\s*(RESOLVED|NOT_RESOLVED|PARTIAL)", l)
        if m and verdict == "UNKNOWN": verdict = m.group(1)
        m = re.match(r"RE-ENTER:\s*(recon|craft|none)", l)
        if m and route == "none" and "RE-ENTER:" in l: route = m.group(1)
    log({"instance":iid,"stage":"audit","depth":depth,"wall_s":round(dt),
         "verdict":verdict,"route":route})
    return out, verdict, route

# ── patch capture / teardown ──────────────────────────────────────────────────

def capture_patch(inst, cid, root, tsha):
    iid = inst["instance_id"]; tag = iid.replace("/","_")
    # Source-only prediction: exclude the test files the official harness owns (it resets
    # them to base and re-applies the gold test patch itself). An incidental agent edit to
    # a test file collides with that re-application and trips git's -R heuristic, reversing
    # the real fix (django-15987 false-positive). Paths come from the test_patch headers.
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    excl = " ".join(f"':(exclude){p}'" for p in testfiles)
    # Strip agent detritus AND generated test artifacts before diffing, so the captured
    # model_patch is the fix, not test-run output (matplotlib result_images, pyc, caches,
    # compiled libs). Without this, `git add -A` swept 100s of KB of artifacts into patches.
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && "
            f"find . -path ./.git -prune -o \\( -name \"*.bak\" -o -name \"*.bak[0-9]*\" -o -name \"*.orig\" -o -name \"*.pyc\" -o -name \"*.so\" \\) -print -delete >/dev/null 2>&1; "
            f"find . -path ./.git -prune -o -type d \\( -name __pycache__ -o -name .pytest_cache -o -name result_images -o -name \"*.egg-info\" \\) -exec rm -rf {{}} + >/dev/null 2>&1; "
            f"git add -A >/dev/null 2>&1; "
            f"git -c core.fileMode=false diff {tsha} -- . {excl}'", timeout=120)
    diag = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && "
               f"echo ===STATUS===; git status --short | head -40; "
               f"echo ===LOG===; git log --oneline -4; "
               f"echo ===STAT===; git diff {tsha} --stat | tail -20'", timeout=120)
    (HERE/f"r4_capture_diag_{tag}.txt").write_text(diag.stdout+diag.stderr)
    if not r.stdout.strip():
        log({"instance":iid,"stage":"capture","msg":"EMPTY patch — see capture_diag"})
    return r.stdout

def verify_gate(inst, cid, root):
    """Driver-side final gate run on the agent's tree, AFTER the loop. Two purposes:
    (1) an independent confirmation of the verdict (we re-run the tests ourselves
    rather than trusting the agent's audit), and (2) the saved passing-test output
    artifact for this trial. Saved per instance as r4_passgate_<id>.txt."""
    tc = (inst.get("install_config") or {}).get("test_cmd","")
    if not tc: return "", None
    act = inst.get("env_activate",""); pre = f"{act} 2>/dev/null; " if act else ""
    r = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && {pre}{tc} 2>&1 | tail -300'", timeout=1800)
    tag = inst["instance_id"].replace("/","_")
    out = f"$ {tc}\n\n{r.stdout}{r.stderr}"
    (HERE/f"r4_passgate_{tag}.txt").write_text(out)
    # independent F2P check — PYTEST-SPECIFIC. For non-pytest runners (django runtests,
    # sympy bin/test) the output isn't "PASSED <id>"-shaped, so return None (unknown)
    # rather than a misleading False. The official grader is the authority regardless.
    f2p = inst.get("FAIL_TO_PASS") or []
    pytest_shaped = ("PASSED" in r.stdout) or re.search(r"\d+ passed", r.stdout)
    if not pytest_shaped:
        return out, None
    def passed(name):
        base = name.split("::")[-1]
        return (f"PASSED {name}" in r.stdout) or (f"{name} PASSED" in r.stdout) or \
               (f"PASSED" in r.stdout and base in r.stdout and f"FAILED {name}" not in r.stdout)
    all_f2p_pass = all(passed(n) for n in f2p) if f2p else None
    return out, all_f2p_pass

def teardown(inst, cid):
    img = inst["image_name"].replace("docker.io/","")
    ssh(f"sudo docker rm -f {cid} 2>/dev/null; sudo docker rmi {img} 2>/dev/null; echo cleaned")

# ── outer loop ────────────────────────────────────────────────────────────────

def process(iid):
    inst = TASKS[iid]
    HERE.mkdir(parents=True, exist_ok=True)
    log({"instance":iid,"stage":"start"})

    s = setup(inst)
    if not s: return
    cid, root, applied, tsha = s
    if not applied: teardown(inst, cid); return

    failbase = warm_and_failbase(inst, cid, root)
    box, gate = helpers(inst, cid, root)
    ssh(f"sudo docker network disconnect bridge {cid} 2>/dev/null; echo done")  # offline

    tag = iid.replace("/","_")
    hgraph = str(HERE/f"r4_hgraph_{tag}.md")
    pathlib.Path(hgraph).write_text(f"# Hypothesis graph: {iid}\n")

    verdict, route, kill_report, handoff = "UNKNOWN", "recon", None, None
    prev_route = None
    for depth in range(MAX_OUTER):
        # RECON — unless audit routed straight back to craft (recon was right)
        if route == "recon" or handoff is None:
            handoff, fixed_point = recon(inst, box, gate, hgraph, kill_report, depth)
            if fixed_point and depth > 0:
                log({"instance":iid,"stage":"halt","msg":"fixed point: re-diagnosis converged"})
                break
        # CRAFT
        craft_out, wants_rediagnose = craft(inst, box, gate, hgraph, handoff, kill_report, depth)
        if wants_rediagnose and depth < MAX_OUTER-1:
            # craft says the hypothesis is wrong — feed its note back to recon next iter
            kill_report = f"craft could not implement the diagnosis:\n{craft_out[-2000:]}"
            route = "recon"; prev_route = None; continue
        # AUDIT
        audit_out, verdict, raw_route = audit(inst, box, gate, hgraph, failbase, depth)
        route = raw_route
        if verdict == "RESOLVED" or route == "none":
            break
        # No-progress escalation: a regression that survived ONE narrow attempt means the
        # approach conflicts with the P2P test — re-diagnosing beats grinding craft (which
        # would just retry the same edit). Allow one narrow, then route recon.
        if route == "craft" and prev_route == "craft":
            log({"instance":iid,"stage":"escalate",
                 "msg":"narrow mode stalled on persistent regression -> route recon (re-diagnose)"})
            route = "recon"
            kill_report = ("NARROW MODE STALLED: a PASS_TO_PASS regression persisted after a "
                           "narrow attempt. The chosen root cause / edit site conflicts with the "
                           "regressed test. Re-diagnose with a DIFFERENT approach.\n" + audit_out[-1800:])
        elif depth < MAX_OUTER-1:
            kill_report = audit_out[-2500:]  # routes recon (re-diagnose) or craft (narrow, first time)
        else:
            log({"instance":iid,"stage":"halt","msg":f"depth budget exhausted at {verdict}"})
        prev_route = raw_route

    # Driver-side final gate: save passing-test output + independently confirm verdict.
    passout, drv_f2p_pass = verify_gate(inst, cid, root)
    log({"instance":iid,"stage":"verify_gate","agent_verdict":verdict,
         "driver_f2p_pass":drv_f2p_pass,
         "passgate_file":str(HERE/f"r4_passgate_{tag}.txt")})

    patch = capture_patch(inst, cid, root, tsha)
    pf = HERE/f"r4_patch_{tag}.diff"; pf.write_text(patch)
    with open(PATCHES,"a") as f:
        f.write(json.dumps({"instance_id":iid,"patch":patch})+"\n")
    log({"instance":iid,"stage":"done","final_verdict":verdict,
         "driver_f2p_pass":drv_f2p_pass,
         "patch_bytes":len(patch),"patch_file":str(pf),"hgraph":hgraph})
    teardown(inst, cid)

if __name__ == "__main__":
    for iid in sys.argv[3:]:
        try: process(iid)
        except Exception as e:
            log({"instance":iid,"stage":"ERROR","msg":f"{type(e).__name__}: {str(e)[:200]}"})
    sys.stderr.write("rung4 driver done\n")
