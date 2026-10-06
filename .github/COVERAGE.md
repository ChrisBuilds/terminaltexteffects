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
- `context.json`: measurement profile, configuration/tool versions, tested revision, and run provenance.

Extract the artifact and open `html/index.html` locally. Reports are retained for 14 days.
No external service, custom token, PR comment bot, or public coverage site is involved.
The reporting step uses the built-in GitHub token with read-only Actions access to retrieve
a main-run artifact; it never executes or extracts artifact code. Where
coverage data exists after failed tests, summary/artifact publication still runs; the
summary identifies the failed test outcome. Do not use incomplete or failing runs as baselines.

Coverage measures `terminaltexteffects`, including unexecuted runtime modules, rather than
tests, development prototypes, or maintenance tools. Xdist worker data is combined by
pytest-cov. The terminal/HTML overall percentage combines lines and branches; the job
summary computes each separately, so avoid comparing unlike metrics.

## Automatic informational comparison

For code-bearing PRs, the Python 3.14 job summary compares separate line and branch counts
and percentages with a successful `CI` push on the **exact PR base commit** on `main`.
Changes are percentage points, not relative percentage changes. Both denominators are shown
because adding or removing code can change the overall percentage without changing tests.
No threshold is enforced: decreases do not fail CI.

The comparison requires a complete successful main workflow, a nonexpired coverage artifact,
and matching metadata: Linux/Python 3.14, default pairwise profile, pytest/coverage configuration,
selection helper/conftest and CI workflow fingerprint, JSON format, and coverage/pytest-cov/pytest/xdist versions.
Artifact metadata must match its run ID, attempt, repository, commit, push event, main branch,
and successful test outcome. Reports from PRs or failed tests cannot become baselines.
The workflow fingerprint is deliberately conservative: any edit to `ci.yml` suppresses
the historical delta, including edits unrelated to coverage, rather than overlooking
changes to test commands, instrumentation or the runner.

Missing/expired artifacts, API failures, changed settings, or a base commit without a successful
coverage run produce **baseline unavailable**, with no numerical delta and no CI failure.
There is no fallback to an older or unrelated commit. Existing artifacts without `context.json`
are intentionally incompatible; the first successful main run after this change seeds comparison.
Documentation-only main commits can also lack an exact coverage baseline because their tests
are skipped. Current collection errors and test failures still fail their existing checks.

The same summary lists added/modified executable runtime lines that current tests did not
exercise. This uses the base-to-tested-commit Git diff and current coverage data, so it can work
even without a compatible historical artifact. Comments and excluded lines are not counted;
rename destinations count as new files. Changed files absent from coverage and unavailable
diffs are reported explicitly. Detail is capped at 20 files/50 missing lines per file; the full
HTML/JSON artifacts remain available. This is changed-line coverage, not changed-branch analysis.

Review missing paths and the context behind a change. Coverage shows which paths executed;
it does not prove useful assertions, visual fidelity, or adequate edge-case testing. Main/manual
runs publish current totals and metadata without fetching a PR baseline. Failed test reports
remain diagnostic, with comparison disabled. No extra test suite, job, or external service runs.

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

Use successful CI runs to measure instrumentation timing. Compare its test-step
time with recent Python 3.14 runs before considering further optimization; coverage runs
once and does not add another suite or matrix job. Do not disable instrumentation merely
to obtain a preferred percentage.
