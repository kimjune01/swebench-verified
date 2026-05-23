import json, glob, os, shutil, subprocess, datetime, sys
# Usage: archive_batch.py <batch_file.json> <grade_glob_base>
#   e.g. archive_batch.py .../tasks/batch_002.json /tmp/grade_batch2box_
REPO="/Users/junekim/Documents/swebench-verified"
SRC="/tmp/swebench-abduction"
BATCH=sys.argv[1]; GBASE=sys.argv[2]
RUNID=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
ids=[b["instance_id"] for b in json.load(open(BATCH))]

official={}
for rep in glob.glob(f"{GBASE}*/report.json"):
    r=json.load(open(rep))
    for i in r.get("resolved_ids",[]): official[i]=True
    for i in r.get("unresolved_ids",[]): official.setdefault(i,False)

def box_logdir(iid):
    for d in glob.glob(f"{GBASE}*/instance_logs/{iid}"):
        return d
    return None

def ledger_lines(iid):
    out=[]
    for lf in glob.glob(f"{SRC}/rung4_results_*.jsonl"):
        for l in open(lf):
            try: o=json.loads(l)
            except: continue
            if o.get("instance")==iid: out.append(l.rstrip("\n"))
    return out

for iid in ids:
    tag=iid.replace("/","_")
    dst=f"{REPO}/results/{iid}/{RUNID}"
    os.makedirs(f"{dst}/official_eval", exist_ok=True)
    for src,dn in [(f"r4_patch_{tag}.diff","patch.diff"),
                   (f"r4_hgraph_{tag}.md","hypothesis_graph.md"),
                   (f"r4_failbase_{tag}.txt","failbase.txt"),
                   (f"r4_passgate_{tag}.txt","passing_tests_our_gate.txt")]:
        p=f"{SRC}/{src}"
        if os.path.exists(p): shutil.copy(p,f"{dst}/{dn}")
    for f in glob.glob(f"{SRC}/r4_out_*_{tag}_d*.txt"):
        base=os.path.basename(f).replace(f"_{tag}","").replace("r4_out_","agent_")
        shutil.copy(f,f"{dst}/{base}")
    with open(f"{dst}/ledger.jsonl","w") as fh: fh.write("\n".join(ledger_lines(iid))+"\n")
    ld=box_logdir(iid)
    if ld:
        for fn in ["report.json","test_output.txt","run_instance.log","eval.sh","patch.diff"]:
            p=os.path.join(ld,fn)
            if os.path.exists(p): shutil.copy(p,f"{dst}/official_eval/{fn if fn!='patch.diff' else 'applied_model_patch.diff'}")
    json.dump({"instance_id":iid,"official_resolved":official.get(iid),
               "run_id":RUNID,"grader":"swebench.harness.run_evaluation",
               "dataset":"princeton-nlp/SWE-bench_Verified"},
              open(f"{dst}/official_eval/summary.json","w"), indent=1)
    subprocess.run(["git","-C",REPO,"add",f"results/{iid}"],check=True)
    verdict="resolved" if official.get(iid) else "UNRESOLVED"
    subprocess.run(["git","-C",REPO,"commit","-q","-m",
        f"run: {iid} @ {RUNID} (official: {verdict})"],check=True)
    print(f"committed {iid:42s} official={verdict}")
print("RUNID:",RUNID, "| resolved:", sum(1 for i in ids if official.get(i)), "/", len(ids))
