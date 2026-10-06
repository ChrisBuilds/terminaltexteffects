# Coverage reporting

The Linux **Python 3.14** job collects runtime-package coverage during its existing default
pytest run. Other Python versions and platform jobs run without instrumentation. Coverage
is reporting-only: test failures still fail CI, but there is no percentage threshold yet.
Documentation-only changes skip tests and coverage; required check names are unchanged.

## Read the reports

Open the CI run and its Python 3.14 job summary for separate line and branch totals and
percentages. Download the `coverage-python-3.14` artifact from the run for:

- `coverage.json`: per-file and total line/branch counts.
- `coverage.xml`: machine-readable Cobertura report.
- `html/index.html`: browsable source with missing lines and branches highlighted.

Extract the artifact and open `html/index.html` locally. Reports are retained for 14 days.
No external service, token, PR comment bot, or public coverage site is involved. Where
coverage data exists after failed tests, summary/artifact publication still runs; the
summary identifies the failed test outcome. Do not use incomplete or failing runs as baselines.

Coverage measures `terminaltexteffects`, including unexecuted runtime modules, rather than
tests, development prototypes, or maintenance tools. Xdist worker data is combined by
pytest-cov. The terminal/HTML overall percentage combines lines and branches; the job
summary computes each separately, so avoid comparing unlike metrics.

## Establish and compare the baseline

Record the first complete successful default-suite CI report in the local development QA
log with its commit, run URL, line/branch counts and percentages, Python/OS, test results,
and test-step duration. A focused local run verifies reporting but is not a project baseline.
The initial baseline is pending that CI run; no percentage target is assumed.

Compare subsequent successful runs with the same scope and configuration. Treat changes
in the statement/branch denominator, skipped tests, or supported environment as context
for differences. Coverage shows which paths executed; it does not prove useful assertions,
visual fidelity, or adequate edge-case testing. Review the missing paths before setting
an eventual regression policy or adding tests.

The baseline uses deterministic pairwise effect-argument coverage. Manual, visual, and
exhaustive pre-release tests remain excluded by the normal pytest configuration. Fresh
installation/artifact checks and other Python/platform jobs run separately and are not
merged into this report. The locked pytest-cov 7 configuration does not instrument arbitrary
CLI subprocesses; their integration checks can pass without contributing coverage. Runtime
code exercised directly in pytest workers contributes normally.

## Reproduce or diagnose

From a synced development environment at the relevant commit:

```sh
./.venv/bin/python -m pytest -n auto --durations=20 \
  --cov=terminaltexteffects --cov-branch --cov-config=pyproject.toml \
  --cov-report=term-missing --cov-report=xml:coverage/coverage.xml \
  --cov-report=json:coverage/coverage.json --cov-report=html:coverage/html
```

Broad local runs remain for diagnosis or explicit requests. For a reporting smoke check,
append one focused test file instead; label the resulting report as partial. Output under
`coverage/` and `.coverage*` is ignored by Git. Normal focused tests remain uninstrumented
unless `--cov` is supplied. For reliable comparisons, use the canonical Linux CI report;
local platform/interpreter/dependency differences may change results and timing.

The initial CI run will also provide instrumentation timing evidence. Compare its test-step
time with recent Python 3.14 runs before considering further optimization; coverage runs
once and does not add another suite or matrix job. Do not disable instrumentation merely
to obtain a preferred percentage.
