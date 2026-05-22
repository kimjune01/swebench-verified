# SWE-bench Known Bad Instances

Instances with broken Docker environments, flaky tests, or invalid setups.
Exclude these for a clean evaluation run.

## Confirmed: Gold Patch Fails

These instances fail even when the correct patch is applied (SWE-bench Issues #267, #294, #372, #484):

```
astropy__astropy-7606
astropy__astropy-7166
astropy__astropy-7336
astropy__astropy-7671
astropy__astropy-8707
astropy__astropy-8872
django__django-10097
matplotlib__matplotlib-20488
pylint-dev__pylint-6528
pylint-dev__pylint-7080
pylint-dev__pylint-7277
sphinx-doc__sphinx-10323
sphinx-doc__sphinx-10435
sympy__sympy-20590
```

## Intermittent / Flaky Tests (Issue #167)

Fail non-deterministically:

```
matplotlib__matplotlib-23987
psf__requests-1963
psf__requests-2317
psf__requests-2674
sympy__sympy-13177
sympy__sympy-13146
```

## External Service Dependencies (unstable)

```
psf__requests-1724
psf__requests-1766
psf__requests-1921
psf__requests-2317
```

## Weak Test Coverage (UTBoost paper, 2026)

Known instances where an incorrect solution can pass the test suite:

```
django__django-13710
django__django-13933
django__django-15278
mwaskom__seaborn-3010
```

(23 total in Lite, 26 in Verified — full list at https://github.com/CUHK-Shenzhen-SE/UTBoost)

## PASS_TO_PASS Regressions

```
matplotlib__matplotlib-24334
```

## Minimum Safe Exclusion List (union of above, deduplicated)

```
astropy__astropy-7166
astropy__astropy-7336
astropy__astropy-7606
astropy__astropy-7671
astropy__astropy-8707
astropy__astropy-8872
django__django-10097
django__django-13710
django__django-13933
django__django-15278
matplotlib__matplotlib-20488
matplotlib__matplotlib-23987
matplotlib__matplotlib-24334
mwaskom__seaborn-3010
psf__requests-1724
psf__requests-1766
psf__requests-1921
psf__requests-1963
psf__requests-2317
psf__requests-2674
pylint-dev__pylint-6528
pylint-dev__pylint-7080
pylint-dev__pylint-7277
sphinx-doc__sphinx-10323
sphinx-doc__sphinx-10435
sympy__sympy-13146
sympy__sympy-13177
sympy__sympy-20590
```

## SWE-bench Lite Subset (verified against princeton-nlp/SWE-bench_Lite)

12 of the 28 known bad instances are present in the 300-instance Lite split:

```
django__django-13710
django__django-13933
matplotlib__matplotlib-23987
matplotlib__matplotlib-24334
mwaskom__seaborn-3010
psf__requests-1963
psf__requests-2317
psf__requests-2674
pylint-dev__pylint-7080
sympy__sympy-13146
sympy__sympy-13177
sympy__sympy-20590
```

The remaining 16 are only in Full/Verified, not Lite.

## Systemic Issues

- **ARM (Apple Silicon)**: 496 containers require x86 emulation — 6.3x slowdown; some images unavailable for arm64
- **Docker hang bug**: Evaluations hang unpredictably near completion (Issues #157, #247); use a per-task timeout
- **Test design flaws**: OpenAI Feb 2026 audit found 59.4% of SWE-bench Verified problems have material test design flaws (narrow implementation-specific checks, undocumented behavior tests)
- **Contamination**: All Verified instances predate Oct 2023 — memorization risk for models trained after that date

## Sources

- https://github.com/swe-bench/SWE-bench/issues/167
- https://github.com/swe-bench/SWE-bench/issues/267
- https://github.com/swe-bench/SWE-bench/issues/294
- https://github.com/SWE-bench/SWE-bench/issues/372
- https://github.com/SWE-bench/SWE-bench/issues/484
- https://arxiv.org/pdf/2506.09289 (UTBoost)
- https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- https://greynewell.com/blog/swe-bench-verified-broken-5-things-source-code/
