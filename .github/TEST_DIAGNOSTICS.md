# Investigating CI test failures

The existing CI test invocations produce JUnit XML and small reproduction metadata.
No additional suite, retry, timeout-failure policy, or required check is introduced.

## Find the evidence

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
