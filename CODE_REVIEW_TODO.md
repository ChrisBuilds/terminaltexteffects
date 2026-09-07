# Engine and Utilities Code Review TODO

Findings from the 2026-09-05 engine and utilities review. Existing engine
and utility tests passed at review time (`992 passed`); the edge cases below
need regression coverage.

## P1 — Correctness and API safety

- [x] Restrict `ParticlePool.reclaim()` to particles owned by that pool.
  - `reclaim()` currently accepts a particle from another pool and adds it to
    `available`, even though `extend()` rejects shared ownership.
  - Verify `ParticlePool._particle_owners[id(character)] is self` before
    mutating visibility, active state, or availability.
  - Add tests for reclaiming a foreign particle and an unowned particle.
  - Files: `terminaltexteffects/engine/effect_support/particles.py`

- [ ] Validate explicitly provided dataclass configuration values.
  - `BaseConfig.__post_init__()` applies defaults but does not validate
    caller-provided values against `ArgSpec` constraints.
  - Example: `TerminalConfig(tab_width=0)` is accepted and parsing a tab
    raises `ZeroDivisionError`.
  - Decide whether direct construction should validate every `ArgSpec` or
    whether a separate validated public constructor is clearer.
  - Add direct-construction tests for invalid terminal and effect config
    values.
  - Files: `terminaltexteffects/engine/base_config.py`,
    `terminaltexteffects/engine/terminal.py`

## P2 — Correctness and API coherence

- [ ] Require exactly six hexadecimal digits for RGB colors.
  - `hexterm.is_valid_color()` currently accepts seven-digit RGB strings.
  - `Color("1234567")` succeeds, but downstream rendering uses only its
    first six digits.
  - Add validation tests for seven digits, repeated `#` characters, and
    normal six-digit values.
  - Files: `terminaltexteffects/utils/hexterm.py`,
    `tests/utils_tests/test_hexterm.py`

- [ ] Normalize and validate all `Gradient.steps` inputs before generation.
  - `Gradient(color, steps=())` raises `IndexError`.
  - `Gradient(color, steps=(0,))` creates an empty spectrum, bypassing the
    documented positive-step requirement.
  - Reject empty tuples and any step less than one with `ValueError`.
  - Files: `terminaltexteffects/utils/graphics.py`,
    `tests/utils_tests/test_gradient.py`

- [ ] Reject an empty symbol sequence in `Scene.apply_gradient_to_symbols()`.
  - An empty sequence reaches `cyclic_distribution()` and raises
    `ZeroDivisionError`.
  - Raise `AnimationSceneError` with a useful message instead.
  - Files: `terminaltexteffects/engine/animation.py`,
    `tests/engine_tests/test_animation.py`

- [ ] Make `Terminal.get_characters_grouped()` consistent for off-canvas added characters.
  - Column and diagonal groupings silently omit some off-canvas added
    characters, while row and center groupings include them.
  - Choose and document one policy: filter all off-canvas characters before
    grouping, or include every selected character in every grouping.
  - Add a parameterized test covering every `CharacterGroup`.
  - Files: `terminaltexteffects/engine/terminal.py`,
    `tests/engine_tests/test_terminal.py`

- [ ] Give `EffectCharacter` terminal-scoped identity, or use object identity.
  - Character IDs restart at zero per `Terminal`, but equality and hashing use
    only `character_id`.
  - The first character from two terminals compares equal and collapses in a
    shared set or dictionary.
  - Add cross-terminal equality/hash tests and audit callers relying on
    equality.
  - Files: `terminaltexteffects/engine/base_character.py`,
    `tests/engine_tests/test_base_character.py`

- [ ] Align `shift_color_towards()` behavior with its extrapolation documentation.
  - Its docstring promises extrapolation for factors outside `[0, 1]`, but
    out-of-range RGB channels produce invalid hex strings and raise
    `ValueError`.
  - Either clamp output channels or reject out-of-range factors and update the
    documentation.
  - Files: `terminaltexteffects/utils/graphics.py`,
    `tests/utils_tests/test_gradient.py`

## P3 — Performance opportunities

- [ ] Remove repeated front-pops from ordinary scene playback.
  - `Scene.get_next_visual()` calls `list.pop(0)` once per completed frame,
    resulting in quadratic work for long scenes.
  - Consider a playback index or an internal deque while preserving the public
    scene-inspection behavior used by effects and tests.
  - Files: `terminaltexteffects/engine/animation.py`

- [ ] Make outside-to-middle character sorting linear.
  - `Terminal.get_characters()` repeatedly calls `pop(0)` for
    `OUTSIDE_ROW_TO_MIDDLE` and `MIDDLE_ROW_TO_OUTSIDE`.
  - Use a deque or index-based interleaving.
  - Files: `terminaltexteffects/engine/terminal.py`

- [ ] Make breadth-first traversal queue operations linear.
  - `BreadthFirst.step()` uses `pop(0)` and linear membership checks against
    `new_edges` and the frontier.
  - Use `collections.deque` and a discovered set while preserving traversal
    order.
  - Files: `terminaltexteffects/utils/spanningtree/algo/breadthfirst.py`

- [ ] Profile terminal frame rendering after the localized queue fixes.
  - `_update_terminal_state()` allocates a full two-dimensional buffer and
    sorts visible characters on every frame.
  - Benchmark before redesigning; consider dirty rows/cells or layer-order
    caching only if profiling shows this is a dominant cost.
  - Files: `terminaltexteffects/engine/terminal.py`

## Verification checklist

- [ ] Add a focused regression test for every fixed correctness item.
- [ ] Run touched engine or utility tests with `./.venv/bin/pytest -n auto`.
- [ ] Run `./.venv/bin/ruff check` on touched implementation and test files.
- [ ] Run `./.venv/bin/pyright --pythonpath ./.venv/bin/python` on touched
  implementation and test files.
- [ ] Re-run relevant performance benchmarks for any P3 change.
