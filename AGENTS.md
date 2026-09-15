# AGENTS.md

## Development Workflow

- Before running project tools, check the project root for a `.venv` and prefer the tool binaries from that environment.
- Use the repo venv paths directly when available:
  - `./.venv/bin/pytest`
  - `./.venv/bin/ruff`
  - `./.venv/bin/pyright`
  - `./.venv/bin/python`

## Docstring Style

- When referencing variables, constants, methods, classes, modules, or other code identifiers in docstrings, use single backticks, such as `ParticlePool`. Do not use double backticks.

## Testing and Verification

- Use focused tests for routine development. Start with the narrowest test node or file that exercises the changed
  behavior; do not run the entire suite after every change.
- Specify a single test, a filtered group, or a complete test file as appropriate:
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py::test_<name>`
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py -k '<expression>'`
  - `./.venv/bin/pytest -n auto tests/engine_tests/test_terminal.py`
- For effect work, the usual focused command is:
  - `./.venv/bin/pytest -n auto tests/effects_tests/test_<effect>.py`
- Default pytest runs exclude tests marked `manual` or `visual`. Run those suites only when their output needs human
  inspection:
  - `./.venv/bin/pytest -m visual tests/test_effects.py`
  - `./.venv/bin/pytest -m manual tests/test_effects.py`
- Highly parametrized effect-configuration tests use deterministic pairwise coverage by default. This covers every
  parameter value and every pair of values without running the complete Cartesian product. Do not pass
  `--exhaustive-effect-args` during normal development.
- Reserve exhaustive effect-argument testing for pre-release validation:
  - `./.venv/bin/pytest -n auto --exhaustive-effect-args`
- Run the default full suite when a change affects shared engine behavior, pytest infrastructure, or several effects:
  - `./.venv/bin/pytest -n auto`
- After targeted pytest passes, run `ruff check` on the touched implementation and test files. For example:
  - `./.venv/bin/ruff check terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`
- After Ruff passes, run Pyright on those same files. For example:
  - `./.venv/bin/pyright --pythonpath ./.venv/bin/python terminaltexteffects/effects/effect_<effect>.py tests/effects_tests/test_<effect>.py`

## Completion Criteria

- Do not consider code work finished until the focused pytest tests and `ruff check` and `pyright` runs for the touched
  files have passed.
- Run the default full suite in addition to focused tests when the change is cross-cutting or changes test collection.
- Run the exhaustive effect-argument suite only as part of pre-release validation, unless the task explicitly requires
  diagnosing the complete parameter matrix.
- Documentation-only changes do not require pytest, Ruff, or Pyright; run an appropriate formatting or diff check.
