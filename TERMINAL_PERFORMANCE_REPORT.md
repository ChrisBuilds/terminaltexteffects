# Terminal Review Performance Report

## Conclusion

The terminal review did introduce a measurable performance cost on legacy ASCII input. Relative to the commit
immediately before the terminal review, the current working tree is approximately 5.5% slower to build effect
iterators, 5.2% slower to render them, and 5.4% slower overall across the tested scenarios.

Almost all of that change entered with wide-character support (`e2af9b6`). The raw-control validation, canvas-bound
corrections, empty-bound handling, and current strict ANSI parser are individually neutral within benchmark noise.

## Method

- Baseline: `352fd1d` (`Align graphics API documentation`), immediately before the terminal review.
- Revisions: baseline plus every terminal-review commit and the current uncommitted issue-5 implementation.
- Effects: `wipe`, `expand`, and `spray`.
- Inputs: harness presets `medium`, `wide`, `tall`, and `color`.
- Per revision/scenario: three independent process runs, each with 3 warmups and 21 timed samples.
- Ordering: chronological, reverse chronological, and interleaved passes to reduce time-order, cache, and thermal bias.
- Environment: the repository `.venv`, seed `1337`, and `PYTHONHASHSEED=0`.
- Aggregation: the median of the three run means for each scenario, followed by an equal-weight arithmetic mean across
  the 12 effect/input scenarios.
- Total measured work: 4,536 timed effect executions and 648 warmup executions.

The benchmark used `tools/perf/benchmark_effects.py`; its build metric includes terminal/canvas initialization and the
effect-specific iterator build. Rendering excludes terminal stdout and frame-rate sleeps.

The harness's `wide` preset is a long ASCII row. That makes it useful for detecting regressions to previously supported
input. Actual wide glyphs cannot be compared behavior-for-behavior with the baseline because that revision did not yet
implement their display-cell semantics.

## Aggregate Commit Series

Times are milliseconds per effect execution, averaged equally across the 12 scenarios. Step deltas compare each row
with the preceding revision; baseline deltas compare with `352fd1d`.

| Revision | Change | Build | Build step | Build baseline | Render | Render step | Render baseline | Total | Total step | Total baseline |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `352fd1d` | Pre-review baseline | 13.566 | — | — | 17.593 | — | — | 31.150 | — | — |
| `db95e26` | Reject raw controls | 13.532 | -0.25% | -0.25% | 17.612 | +0.11% | +0.11% | 31.165 | +0.05% | +0.05% |
| `e2af9b6` | Support wide symbols | 14.236 | +5.20% | +4.94% | 18.458 | +4.81% | +4.92% | 32.702 | +4.93% | +4.98% |
| `61bd36c` | Correct canvas bounds | 14.299 | +0.44% | +5.40% | 18.426 | -0.18% | +4.74% | 32.722 | +0.06% | +5.05% |
| `1d0d077` | Handle empty bounds | 14.368 | +0.49% | +5.92% | 18.477 | +0.28% | +5.03% | 32.834 | +0.34% | +5.41% |
| current | Strict ANSI parsing | 14.316 | -0.36% | +5.53% | 18.506 | +0.16% | +5.19% | 32.816 | -0.05% | +5.35% |

The approximately half-percent movements after `e2af9b6` are smaller than normal between-pass variation and do not
show a consistent build/render direction. The wide-symbol step is the only clear series discontinuity.

## Current Versus Baseline by Effect

| Effect | Build | Delta | Render | Delta | Total | Delta |
|---|---:|---:|---:|---:|---:|---:|
| Wipe | 13.910 → 14.677 ms | +5.51% | 6.662 → 7.211 ms | +8.25% | 20.577 → 21.902 ms | +6.44% |
| Expand | 14.553 → 15.400 ms | +5.82% | 17.405 → 17.965 ms | +3.21% | 31.927 → 33.342 ms | +4.43% |
| Spray | 12.234 → 12.871 ms | +5.21% | 28.711 → 30.341 ms | +5.68% | 40.945 → 43.205 ms | +5.52% |

## Current Versus Baseline by Input Shape

| Input | Build | Delta | Render | Delta | Total | Delta |
|---|---:|---:|---:|---:|---:|---:|
| Medium | 5.517 → 5.973 ms | +8.26% | 5.372 → 5.733 ms | +6.71% | 10.885 → 11.689 ms | +7.38% |
| Wide ASCII | 5.605 → 5.933 ms | +5.85% | 8.774 → 9.209 ms | +4.96% | 14.374 → 15.148 ms | +5.39% |
| Tall | 39.949 → 41.836 ms | +4.72% | 52.063 → 54.792 ms | +5.24% | 91.976 → 96.601 ms | +5.03% |
| ANSI color | 3.193 → 3.522 ms | +10.33% | 4.161 → 4.289 ms | +3.07% | 7.365 → 7.827 ms | +6.27% |

On the ANSI-color preset specifically, the current strict-parser change versus `1d0d077` measured +0.63% build,
+0.47% render, and +0.72% total. The all-scenario result for the same step was -0.36%, +0.16%, and -0.05%, so no
meaningful issue-5 regression is evident.

## Attribution

A harness `--profile` comparison of Wipe with tall input around the wide-character commit (`db95e26` → `e2af9b6`)
showed:

- Total profiled calls increased from 488,416 to 586,728.
- `get_symbol_cell_width()` entered the hot path with 8,370 calls and about 12 ms cumulative profiler time.
- Profiled `Terminal.__init__()` cumulative time increased from about 11 ms to 16 ms.
- Profiled `_preprocess_input_data()` cumulative time increased from about 5 ms to 9 ms.
- Width-aware visual formatting and continuation-cell rendering also account for the render-side increase.

Profiler timings include instrumentation overhead and should not be read as wall-clock deltas, but the call counts and
commit boundary identify repeated symbol-width calculation as the primary optimization target. Caching width on
immutable symbols/visuals or adding an inexpensive ASCII fast path should be evaluated separately with the same matrix.

## Behavioral Checks and Caveat

Frame counts were identical for every matching effect/input scenario across all revisions and passes.

Output-character totals were not fully stable, including between separate processes running the same historical
revision. Fixing `PYTHONHASHSEED` did not remove every difference because same-layer collision ordering depended on
set/object iteration order at the time of this commit-series measurement. Issue 7 subsequently established stable
`(layer, character_id)` painter semantics; its candidate benchmark produced identical output counts across repeated
processes, so future comparisons can use exact output counts as a behavioral check.

## Issue 7 Deterministic Painter Order

Issue 7 was measured separately against the issue-6 working tree across Wipe, Expand, and Spray with medium, tall, and
generated inputs. Each scenario used two order-balanced process runs with 3 warmups and 21 timed samples per run.

An initial `(layer, character_id)` tuple key was rejected because it increased aggregate render time by 20.5%. The
accepted implementation maintains a character-ID-ordered visibility list when membership changes, then relies on
Python's stable sort with a cached C-level layer key in the frame loop. It measured +0.60% build, -1.20% render, and
-0.50% total time; the corresponding median scenario deltas were +0.42%, -0.55%, and +0.15%. These results are within
normal run variation and show no meaningful frame-loop regression. Frame counts were unchanged, and candidate output
counts were identical across repeated processes.

## Follow-up Rendering and Line-Profile Study

### Conclusion

A follow-up prompted by a visually lower frame rate confirms a rendering regression on legacy ASCII input and a much
larger cost when true double-cell symbols activate the wide-character rendering path. The regression entered primarily
with wide-character support (`e2af9b6`), not with deterministic collision ordering or empty-input handling.

Across the exact Wipe, Expand, and Spray effect/input matrix used by the original study, current `95147f7` is 7.60%
slower to build, 5.64% slower to render, and 6.47% slower overall than pre-review `352fd1d`. These results corroborate
the first study with independently collected data and extend it with additional effects and line-level attribution.

### Method

- Revisions: `352fd1d`, `db95e26`, `e2af9b6`, `61bd36c`, `1d0d077`, `a2abdf7`, `f533bc2`, and `95147f7`.
- Main effects: Wipe, Expand, and Spray with `medium`, wide-ASCII, `tall`, `generated`, and ANSI-color presets.
- Simple controls: Highlight and RandomSequence with `medium`, wide-ASCII, `tall`, and `generated` presets.
- Additional complex effects: Rings and Blackhole with `medium`, wide-ASCII, and `tall` presets. The generated Rings
  case was excluded after a pilot showed roughly one minute per revision without adding a distinct renderer path.
- Each commit-series scenario used two order-balanced independent process runs, 3 warmups per run, and 11 timed
  samples. Rings and Blackhole used 9 timed samples per run.
- The true-wide comparison used `tests/testinput/wide_characters_and_emoji.txt` and an ASCII surrogate with identical
  logical cell geometry and the same number of visible `EffectCharacter` instances. It used two order-balanced runs,
  3 warmups, and 11 timed samples per input.
- Environment: repository `.venv`, Python 3.14.3, seed `1337`, and `PYTHONHASHSEED=0`.
- Total accepted work: 5,132 timed effect executions, 1,452 warmups, 15 call profiles, and 17 line profiles.
- Timings use `tools/perf/benchmark_effects.py`; render time excludes terminal stdout, terminal-emulator drawing, and
  frame-rate sleeps.

An initial pilot was discarded after a traceback showed that the editable virtual-environment installation caused
historical harness scripts to import the current working-tree package. Accepted runs explicitly put each exported
snapshot first on `PYTHONPATH`; module `__file__` and the expected absence/presence of `get_symbol_cell_width()` were
checked at the pre-wide and current boundaries before rerunning.

### Exact Original-Scenario Comparison

Times are milliseconds per effect execution, averaged equally across Wipe, Expand, and Spray with `medium`, wide-ASCII,
`tall`, and ANSI-color input. Baseline deltas compare with `352fd1d`.

| Revision | Change | Build | Build baseline | Render | Render baseline | Total | Total baseline |
|---|---|---:|---:|---:|---:|---:|---:|
| `352fd1d` | Pre-review baseline | 12.973 | — | 17.431 | — | 30.405 | — |
| `db95e26` | Reject raw controls / immediately pre-wide | 13.181 | +1.60% | 17.564 | +0.76% | 30.745 | +1.12% |
| `e2af9b6` | Support wide symbols | 13.936 | +7.42% | 18.505 | +6.16% | 32.440 | +6.70% |
| `61bd36c` | Correct canvas bounds | 13.943 | +7.47% | 18.680 | +7.16% | 32.623 | +7.30% |
| `1d0d077` | Handle empty bounds | 13.986 | +7.81% | 18.566 | +6.51% | 32.552 | +7.06% |
| `a2abdf7` | Harden ANSI parsing | 13.894 | +7.10% | 18.656 | +7.03% | 32.550 | +7.06% |
| `f533bc2` | Stabilize color/collision state | 13.927 | +7.35% | 18.446 | +5.82% | 32.373 | +6.47% |
| `95147f7` | Define empty-input behavior | 13.959 | +7.60% | 18.414 | +5.64% | 32.373 | +6.47% |

The `db95e26` to `e2af9b6` transition remains the only consistent discontinuity. Deterministic painter ordering reduced
render time slightly in this aggregate, and issue 8 had no measurable effect on nonempty rendering.

### Render Delta by Effect

Effect aggregates use the applicable input shapes listed in the method. The wide step compares immediately pre-wide
`db95e26` with `e2af9b6`; the current delta compares `352fd1d` with `95147f7`.

| Effect | Wide-support step | Current vs pre-review |
|---|---:|---:|
| Wipe | +8.12% | +7.16% |
| Highlight | +8.73% | +4.32% |
| RandomSequence | +7.65% | +6.16% |
| Expand | +7.99% | +3.17% |
| Spray | +5.49% | +2.39% |
| Rings | +2.94% | -1.65% |
| Blackhole | +4.06% | +5.67% |

Wipe is consistently slower for every tested legacy input: +9.68% on `medium`, +10.60% on wide ASCII, +11.10% on
`tall`, and +6.03% on generated 80-by-24 input. Frame counts and output-character counts are identical in every Wipe
comparison. All other matching scenarios also retain their frame counts; output counts can differ for moving effects
because current deterministic same-layer collision ordering replaced the historical nondeterministic order.

### True Wide-Character Cost

The ASCII surrogate replaces every double-cell code point with one printable ASCII character followed by an unstyled
gap. This preserves canvas dimensions, logical coordinates, and visible-character count while keeping the renderer on
its ASCII fast path.

| Effect | ASCII surrogate render | True-wide render | Wide-path cost |
|---|---:|---:|---:|
| Wipe | 4.188 ms | 7.420 ms | +77.2% |
| Expand | 4.361 ms | 5.767 ms | +32.2% |
| Spray | 13.039 ms | 18.954 ms | +45.4% |
| Rings | 284.652 ms | 324.858 ms | +14.1% |
| Blackhole | 62.578 ms | 68.489 ms | +9.4% |

The frame counts match within each pair. Output-character counts intentionally differ because a double-cell code point
and its ASCII-plus-gap surrogate have different Python string lengths.

### Call and Line Attribution

Call profiling around `db95e26` to `e2af9b6` shows that the wide-support commit increased Wipe/tall calls from 488,416
to 586,728. Current code remains at 553,790 calls. `Terminal._update_terminal_state()` cumulative cProfile time changed
as follows:

| Effect/scenario | Pre-wide | Wide commit | Current |
|---|---:|---:|---:|
| Wipe/tall | 13 ms | 20 ms | 15 ms |
| Expand/tall | 14 ms | 18 ms | 13 ms |
| Spray/tall | 54 ms | 76 ms | 59 ms |
| Rings/medium | 33 ms | 48 ms | 36 ms |
| Blackhole/tall | 112 ms | 159 ms | 121 ms |

The deterministic ordered-visibility-list implementation recovers much of the initial renderer cost, but two remaining
hot paths are clear:

1. On ASCII frames, `_update_terminal_state()` scans every visible character with
   `all(character.animation.current_character_visual.cell_width == 1 ...)` before rendering. This line alone accounts
   for 15.4% to 17.2% of line-profiled renderer time across Wipe, Expand, Spray, Rings, and Blackhole.
2. Once any visible wide symbol is encountered, the renderer creates ownership and footprint bookkeeping and performs
   overlap detection for every subsequently painted character. Creating the per-character overlap set consumes about
   30% of wide-path renderer time in Wipe and Spray. The dense ownership-buffer allocation itself is only about 1%; the
   repeated Python set/dictionary work and additional per-character passes dominate.

For the controlled wide fixture, line-profiled `_update_terminal_state()` increased from 11.639 to 41.912 ms for Wipe,
25.711 to 104.167 ms for Spray, and 79.117 to 161.396 ms for Blackhole. These are instrumented totals and should not be
read as normal wall-clock timings, but they localize the additional work reliably.

`get_symbol_cell_width()` is a separate build-time target. Wipe/tall invokes it 8,370 times and spends about 12 ms
cumulatively under cProfile; Expand invokes it 7,362 times, Spray 5,850 times, and Blackhole 14,274 times. Repeated
symbol validation and Unicode width lookup explain much of the iterator-build regression but not the between-frame
slowdown.

### Optimization Targets

1. Remove the full visible-character width scan from the ASCII frame path. Track whether a frame can contain a
   double-cell visual, or update a cheap counter/state flag when current visuals change.
2. Replace unconditional per-character overlap-set construction in the wide path with direct one-/two-cell owner
   checks and skip collision bookkeeping when both target cells are unowned.
3. Evaluate sparse owner tracking for wide footprints; do not focus first on dense owner-buffer allocation because its
   measured contribution is small.
4. Cache symbol-width validation or add a dedicated ASCII fast path in `get_symbol_cell_width()` to reduce build cost.
5. Preserve the current deterministic painter order, which is not responsible for the regression and recovered part of
   the original wide-support cost.

### Frame-Rate Interpretation

Measured Python generation remains below the 16.67 ms budget for 60 FPS on these fixtures, including true-wide input.
The engine regression is real, but it is not by itself large enough to explain missed 60 FPS for the tested sizes.
Terminal stdout and terminal-emulator glyph drawing are deliberately outside the harness; emoji and double-cell glyphs
may make that external portion more expensive. End-to-end PTY/terminal-emulator measurement would be required to
attribute any remaining visual slowdown beyond the engine costs identified here.

## Issue 10: Shared Effect Terminal Lifecycle

### Method

The benchmark harness was first extended with a `terminal-output` lifecycle mode while the original engine behavior
was still present. This mode times context entry and canvas preparation, iterator construction, frame generation,
in-memory `Terminal.print()` calls, and context restoration. Baseline reports were captured before changing
`BaseEffect`, then repeated with the shared-terminal implementation using identical inputs, seeds, warmups, and sample
counts. Iterator-only scenarios were also compared to check that the handoff adds no meaningful cost to callers that
do not use `terminal_output()`.

The primary pass used 11 timed samples and three warmups per scenario on the `medium` input. Blackhole received a
separate 21-sample confirmation after its initial seven-sample run showed contradictory render movement. Wipe also ran
on the generated 80-by-24 input for a larger terminal graph.

### End-to-End Results

| Effect/input | Build delta | Render delta | Total delta |
|---|---:|---:|---:|
| Wipe/medium | -10.98% | +2.47% | -6.42% |
| Expand/medium | -5.66% | +5.52% | -2.32% |
| Spray/medium | -12.76% | +1.97% | -3.36% |
| Rings/medium | -12.21% | +4.95% | +3.34% |
| Blackhole/medium, 21 samples | -18.96% | -1.33% | -3.41% |
| Wipe/generated 80 x 24 | -7.93% | +1.24% | -5.29% |

Build time improved in every confirmed scenario because the output context no longer constructs a second character,
fill, and neighbor graph. Render code is unchanged; its small positive and negative movements reflect timing noise.
Rings is render-dominated, so a roughly 5% noisy render movement outweighed its 12% build improvement in that pass.
A follow-up 21-sample candidate run narrowed the Rings iterator-only render difference from +7.01% to +1.40%.

Frame counts and output-character counts matched in every baseline/candidate pair. A generated-input cProfile run
records one `Terminal.__init__()` call for the complete output lifecycle. Tests additionally verify object identity for
both context-before-iterator and iterator-before-context orderings, fresh repeated iterators, nested and repeated
contexts, exception cleanup, and a single detected terminal-dimension snapshot.
