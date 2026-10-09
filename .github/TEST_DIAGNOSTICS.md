# Investigating CI test failures

The existing CI test invocations produce JUnit XML and small reproduction metadata.
No additional suite, retry, timeout-failure policy, or required check is introduced.

## Find the evidence

### Nix failures

For `Nix / Linux` or `Nix / macOS`, inspect the first failing installer or packaging
step and retain its Actions log. Packaging checks additionally upload seven-day
`nix-validation-Linux` / `nix-validation-macOS` log artifacts on success or failure;
cancelled runs may not upload them. These checks do not produce JUnit/context JSON.
The packaging log records the tested Git SHA (possibly the PR merge revision), Nix
version, actual system identifier, and build/smoke evidence. Successful jobs also
write a step summary. The verifier reports the failing script line and compares
checkout/clean/dirty source identities; a mismatch includes file-difference names
without file contents. Missing logs, skipped/cancelled jobs, or an installer failure
are not successful packaging validation.

Temporary source fixtures use physical paths so macOS `/var` and `/private/var`
aliases do not change filter prefixes. Source evaluation uses read/write mode to
materialize filtered store paths for comparisons and diagnostic inspection.

Reproduce at the tested revision with `bash tools/check_nix.sh`, Nix's
`nix-command`/`flakes` features enabled, and Python 3.10+ available. Use the locked
input, not an unrelated local channel. Preserve the original build/runtime error
before fixing source or an evidence-backed infrastructure problem; do not update
the lock or retry to conceal the failure. See [Nix coverage](CI.md#nix-packaging-validation)
for platform limits. Terminal rendering still needs human inspection.

### Python test failures

Open the failed job and its first failing step. Download its seven-day artifact:

| Job | Artifact |
| --- | --- |
| Code quality | `test-results-quality` |
| Linux matrix | `test-results-python-<version>` |
| Native platforms | `test-results-Windows-python-3.14` or `test-results-macOS-python-3.14` |

`context.json` records the tested SHA, PR head/base, actual interpreter/platform,
pytest/xdist/coverage versions, CPU count, and workflow run/attempt. A PR's tested
SHA can be GitHub's merge revision rather than its issue-branch head. No credentials,
environment dump, executable paths, or local filesystem inventory are collected.
Exact selection and flags remain in the workflow's test step and run logs.

JUnit reports record test identifiers, outcomes, durations, and failure details.
Quality steps and Windows hook tests use separate filenames so later invocations do
not overwrite earlier reports. Successful-test output is not included. Failure
details may still contain assertion values or captured output; use synthetic test
data and never print credentials. Reports are diagnostics, not a substitute for
the pytest exit status or the required check result.

Uploads run after success or failure if context exists and the job is not cancelled.
An installation failure can prevent context creation; a setup failure after that can
produce metadata without XML. Cancellation, hard termination, or job timeout can
leave XML incomplete or prevent upload. Missing reports do not imply tests passed.
Use workflow logs when artifacts are missing or expired. Documentation-only matrix
and native jobs generate no reports because their tests are skipped; Code quality
still reports the regression tests it actually executes.

## Diagnose a stalled test

Each CI pytest invocation uses `-o faulthandler_timeout=120`. A test spending over
120 seconds in setup, call, or teardown dumps thread tracebacks to the job log.
This timer does not stop the test, add a retry, or change its exit status. Existing
job timeouts remain the limit; collection or a subprocess stall outside a test may
not produce this dump, and a traceback may only show where a parent is waiting.
Worker tracebacks are available for xdist runs too. Inspect them before cancelling.
The JUnit file is finalized at session end, so it may not exist for a hung session.

## Reproduce narrowly

1. Record the run/attempt, tested revision, interpreter and failing node from the
   context, report and log. Preserve these links in the issue/PR or handoff checkpoint.
2. Fetch/check out that exact tested revision in a separate worktree when available;
   do not replace it with a newer PR head and call that the same reproduction.
3. Install its locked tools with the recorded Python version. Native Python 3.9
   uses `--no-default-groups --group test` in a separate environment; docs/release/hooks
   need modern Python. Match native OS/shell and relevant coverage flags if involved.
4. Run only the failing node first, with detailed output:

   ```sh
   ./.venv/bin/python -m pytest 'tests/path.py::test_name[case]' -vv --tb=long -o faulthandler_timeout=120
   ```

   Use `.venv/Scripts` or `uv run --no-sync` on native Windows. If it passes alone,
   reproduce the relevant neighboring tests/xdist selection and original worker count
   before broadening further. A passing retry does not erase the original failure.
5. For randomized effects, inspect the test's actual seed/input. There is no global
   replay seed captured by this reporting change. If the original seed is unavailable,
   say so; add focused deterministic evidence when diagnosing rather than inventing
   a seed or adding blanket retries. Distinguish test failures from infrastructure,
   dependency installation, and worker-process failures.

See [pytest fault handling](https://docs.pytest.org/en/stable/how-to/failures.html#fault-handler)
and [JUnit output](https://docs.pytest.org/en/stable/how-to/output.html#creating-junitxml-format-files).
