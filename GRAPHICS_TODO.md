# Graphics Utility TODO

Review scope: `terminaltexteffects/utils/graphics.py`, its focused tests in
`tests/utils_tests/test_gradient.py`, the public documentation, and representative engine/effect callers.
Work through correctness items before performance or cleanup items because the mapping changes may intentionally alter
effect output. Keep compatibility aliases or release-note breaking changes where public behavior is changed.

## Correctness

- [x] **1. Normalize coordinate gradients from the actual lower bound to the actual upper bound**
  - Decision: a `1 x 1` mapping uses the first gradient color in every direction.
  - `build_coordinate_color_mapping()` currently calculates horizontal and vertical fractions as
    `(coordinate - (minimum - 1)) / (maximum - (minimum - 1))`, so the first coordinate is never sampled at fraction
    `0`. Diagonal mapping has the same one-cell offset in both axes.
  - This is observable when the spectrum has more colors than the mapped span: a two-column, 11-color black-to-white
    horizontal gradient starts at `808080`, and the equivalent diagonal map starts at `cccccc`, rather than at the
    first stop (`000000`).
  - Normalize non-degenerate axes with `(coordinate - minimum) / (maximum - minimum)`. Define an explicit policy for
    a one-cell axis/rectangle instead of relying on the current denominator trick.
  - Make degenerate behavior coherent across directions. A `1 x 1` horizontal/vertical/diagonal mapping currently
    chooses the final spectrum color, while radial mapping chooses the first.
  - Add exact endpoint tests for two-cell spans, offset bounds, gradients whose spectra are shorter and longer than
    the coordinate span, each direction, and `1 x 1` mappings.
  - Audit representative effects after the change because nearly every effect uses this method for its final color
    map and some existing visuals may have implicitly compensated for the offset.

- [x] **2. Make fractional lookup mathematically defined and reject non-finite input**
  - Decision: select the nearest spectrum sample with `round(fraction * (len(spectrum) - 1))`, matching engine frame
    selection. Exact half-sample ties use Python's round-to-even behavior.
  - Verification: the `synthgrid` generated-input benchmark improved mean build time by 3.53% and mean total time by
    1.45%; mean render time remained effectively flat at +0.56%, with unchanged frame counts.
  - `get_color_at_fraction()` uses a linear scan over `i / len(spectrum)`. This divides `[0, 1]` into `N` buckets
    instead of mapping the interval to the `N` sample positions from index `0` through `N - 1`; values exactly on a
    bucket boundary are also biased toward the lower bucket.
  - Choose and document a quantization rule, preferably an O(1) index calculation based on `len(spectrum) - 1`, and
    use the same rounding policy as other frame/sample selection APIs.
  - Explicitly reject `NaN` and non-numeric values. `NaN` passes the current range check and returns the last color.
  - Add tests around every sample boundary, just below and above boundaries, `0`, `1`, `NaN`, infinities, and invalid
    types.

- [x] **3. Validate `Color` inputs by type before value membership checks**
  - Decision: public `hexterm.is_valid_color()` accepts any object and returns `False` for unsupported types;
    `Color` preserves its documented `ValueError` for invalid constructor values.
  - `hexterm.is_valid_color()` uses `color in range(256)` for every non-string. Because `bool` is an `int` subclass
    and numeric equality is permissive, `Color(True)` is accepted as XTerm color 1 and `Color(1.0)` passes validation
    but leaves a float in `rgb_color`, causing delayed failures elsewhere.
  - Reject booleans and all values other than `int` and `str` at the `Color` boundary, with an exception type and
    message consistent with the documented constructor contract. Consider tightening `hexterm.is_valid_color()` too,
    since it is independently public.
  - Add direct tests for booleans, floats, bytes, `None`, malformed strings, and both integer endpoints.

- [x] **4. Fix reconstructible representations**
  - Decision: representations preserve the original RGB-vs-XTerm `Color` argument and always show both `ColorPair`
    constructor parameters as `fg` and `bg`.
  - `repr(Color(0))` is `Color('0')`, but that string argument is invalid. Render integer `color_arg` values without
    quotes and strings with normal string repr escaping.
  - The dataclass-generated `repr(ColorPair(...))` uses the non-init field names `fg_color` and `bg_color`, while the
    constructor accepts only `fg` and `bg`; evaluating or copying the displayed constructor raises `TypeError`.
  - Add round-trip repr tests for RGB and XTerm `Color` objects and for empty, foreground-only, background-only, and
    two-channel `ColorPair` objects.

## API coherence and data model

- [x] **5. Define `Color` identity, normalization, and mutability semantics**
  - Decision: equality and hashing use normalized specification identity. RGB strings are normalized to lowercase
    without a leading `#`, while XTerm indices remain distinct from RGB specifications and from other indices because
    their exact palette codes affect terminal rendering. `Color` instances are immutable value objects.
  - Equality and hashing currently use the original `color_arg`, so `Color("FFFFFF") != Color("ffffff")` even though
    they emit the same RGB color. `Color(0) != Color("000000")` also distinguishes source encoding rather than visual
    color. Decide whether equality means visual RGB identity or specification identity and document the result.
  - At minimum, normalize hex case. If XTerm provenance must remain significant for output-mode decisions, represent
    that distinction explicitly rather than letting incidental input spelling control equality.
  - `Color` is hashable and is used as a dictionary key and as an argument to the cached `shift_color_towards()`, but
    `color_arg`, `xterm_color`, and `rgb_color` are publicly mutable. Mutation can invalidate dictionary/cache keys or
    put the three attributes in contradictory states. Make colors immutable, or remove hashing/caching contracts that
    require immutability.
  - Add equality/hash tests for case variants, equivalent XTerm/RGB values according to the chosen policy, and mutation
    behavior.

- [x] **6. Make the `Gradient` construction contract internally consistent**
  - Decision: steps count transitions between adjacent stops, so a multi-stop spectrum contains
    `sum(effective_steps) + 1` colors and a single-stop spectrum contains one color. One step value broadcasts to all
    transitions, shorter tuples repeat their last value, and tuples with unused extra values are rejected for
    multi-stop gradients. Single-stop gradients validate all step values but ignore tuple cardinality for compatibility
    with effect configurations. Looping adds a local closing transition without changing the source stops.
  - The general documentation says a spectrum contains `sum(steps) + 1` colors, but a single-stop gradient contains
    exactly `steps` colors. Decide whether `steps` means transitions, output samples, or repetitions, then document and
    test one-stop and multi-stop behavior consistently.
  - A short step tuple repeats its last value while an overlong tuple is silently truncated. Either validate tuple
    cardinality or document both expansion and truncation; silent truncation can hide configuration mistakes.
  - `loop=True` mutates `_stops` by appending the first stop during generation, so the stored/displayed stop list no
    longer represents the constructor input. Keep source stops immutable and build a local pair sequence for the loop.
  - Validate that every stop is a `Color` at construction time so invalid input fails with a clear boundary error
    instead of a later `AttributeError` during generation or printing.
  - Remove the unused `_index` attribute and its documentation unless stateful, single-pass iteration is intentionally
    restored. Current iteration correctly delegates to the spectrum and is restartable.

- [ ] **7. Simplify `ColorPair`'s public shape**
  - The dataclass exposes stored fields named `fg_color`/`bg_color` but initializer-only parameters named `fg`/`bg`.
    This produces the broken repr above and makes dataclass introspection, pattern matching, serialization, and IDE
    discovery disagree with normal construction.
  - Prefer one canonical pair of public field names. If retaining `fg`/`bg` construction for compatibility, provide
    deliberate aliases or a hand-written initializer/repr rather than using `InitVar` as the public API façade.
  - Decide whether the pair should be immutable alongside `Color`; immutable value objects are safer for scene frames
    and shared preexisting-color state.

- [ ] **8. Reject unsupported gradient directions instead of returning an empty map**
  - `build_coordinate_color_mapping()` falls through and returns `{}` for any value not equal to a known
    `Gradient.Direction`. This turns a bad argument into a later missing-key failure in effects.
  - Validate `direction` before allocating the map and raise a clear `TypeError` or `ValueError`, consistent with the
    enum-validation conventions used elsewhere in the project.
  - Also reject boolean/non-integer coordinate bounds explicitly if runtime validation remains part of this method.

## Performance and maintainability

- [ ] **9. Remove spectrum-length work from every coordinate lookup**
  - The linear scan in `get_color_at_fraction()` makes radial and diagonal map construction
    `O(rows * columns * spectrum_length)`. An O(1) fractional index makes the same operation proportional only to the
    number of output coordinates.
  - For horizontal and vertical directions, build the per-axis color list once and populate coordinates from it.
    For radial and diagonal directions, keep one calculation per output coordinate; avoid adding another large cache
    whose keys are unique to a single mapping.
  - Benchmark a large radial/diagonal canvas with short and long spectra before and after the change, and verify the
    generated mapping exactly against the selected quantization contract.

- [ ] **10. Consolidate RGB interpolation and conversion work**
  - `Gradient._generate()` uses `Color.rgb_ints` and `round()`, while `shift_color_towards()` reparses six hex slices,
    normalizes to floats, defines a nested interpolation function on every cache miss, and truncates with `int()`.
    The APIs therefore disagree at half-channel values (`000000` toward `ffffff` at `0.5` becomes `7f7f7f`, while
    gradient generation uses nearest rounding).
  - Select one rounding rule and share a small RGB interpolation primitive. Use already parsed/eager RGB tuples if
    `Color` becomes immutable.
  - Re-evaluate the global 8,192-entry `lru_cache` after simplifying the calculation. Keep it only if effect-level
    profiling shows a useful hit rate, and expose cache behavior deliberately if callers/tests are expected to manage
    it.

- [ ] **11. Align public documentation with actual return types and contracts**
  - `docs/engine/utils/color.md` and `docs/engine/utils/gradient.md` say iteration yields a hex string, but `Gradient`
    yields `Color` objects.
  - Correct the `Gradient` typo ("One ore more"), step-count wording, loop semantics, coordinate endpoint policy,
    `Color` equality semantics, and exception contracts once the decisions above are implemented.
  - Add concise examples for coordinate mappings and for foreground-only/background-only `ColorPair` construction.

## Verification for each implemented item

- `./.venv/bin/pytest -n auto tests/utils_tests/test_gradient.py`
- Run directly affected animation, terminal, and effect tests when value semantics or coordinate mapping changes.
- `./.venv/bin/ruff check terminaltexteffects/utils/graphics.py` plus every touched test/document-adjacent Python file.
- `./.venv/bin/pyright --pythonpath ./.venv/bin/python terminaltexteffects/utils/graphics.py` plus every touched test file.
- After targeted checks pass, run all tests in every touched test file as required by the repository workflow.
