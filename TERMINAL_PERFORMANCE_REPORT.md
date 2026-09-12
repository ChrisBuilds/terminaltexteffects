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

Output-character totals were not fully stable, including between separate processes running the same revision. Fixing
`PYTHONHASHSEED` did not remove every difference because same-layer collision ordering currently depends on set/object
iteration order. That is the separately identified deterministic-collision issue. Output-byte differences therefore
cannot be attributed reliably to this commit series until that issue is resolved; they do not coincide with frame-count
changes.
