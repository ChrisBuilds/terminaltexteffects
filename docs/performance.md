# Performance Testing

Use `tools/perf/benchmark_effects.py` for repeatable effect performance checks. The harness uses only the Python
standard library, disables frame-rate sleeps, renders through the library iterator API, and avoids terminal output.

## Baseline

Run a baseline before changing performance-sensitive code:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --effect wipe \
  --input-preset medium \
  --json-out /tmp/tte-baseline.json
```

Use `--effect all` for a broader pass, and use
`--input-preset small|medium|large|wide|tall|color|sparse|unicode|generated` to
select the input shape. Defaults are `--samples 7`, `--warmups 2`, and `--seed 1337`.

The `sparse` preset creates an 80-by-24 virtual canvas containing only two input characters. It is intended to expose
costs that scale with canvas area instead of visible character count; `generated` provides a dense 80-by-24 control.
The `unicode` preset combines ASCII with CJK, full-width, and single-code-point emoji symbols to exercise double-cell
layout and rendering. The `wide` preset remains a long row of single-cell ASCII and measures input shape, not glyph
display width.

Pass `--memory` to record peak traced Python memory for iterator construction and for the complete iteration. Memory
tracking adds substantial runtime overhead, so compare timing results only with another `--memory` report. Report
comparison includes memory deltas automatically when both inputs contain memory measurements.

The default `--lifecycle iterator` mode measures iterator construction and frame generation without output. Use
`--lifecycle terminal-output` to include the complete public context-manager workflow: terminal preparation, iterator
construction, frame generation, in-memory calls to `Terminal.print()`, and cursor restoration. This mode is useful for
finding duplicated setup or output-lifecycle regressions without writing control sequences to the real terminal.

## Candidate

After making a focused change and running the relevant functional checks, rerun the same benchmark arguments:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --effect wipe \
  --input-preset medium \
  --lifecycle terminal-output \
  --json-out /tmp/tte-candidate.json
```

Compare the two reports:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --compare /tmp/tte-baseline.json /tmp/tte-candidate.json
```

The comparison is advisory by default. Report build, render, and total mean deltas along with frame-count or output-size
changes, but do not treat regressions as failures unless a task explicitly sets a threshold.

## Profiling

Use `--profile` when the timing delta needs a call-level explanation:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --effect wipe \
  --input-preset medium \
  --samples 1 \
  --warmups 0 \
  --profile
```

The profile reports cumulative time for one scenario and is best used after a benchmark shows a meaningful change.

## Opt-in row caching

An effect can call `self.terminal.enable_row_cache()` to reuse formatted rows until their characters change.
The engine tracks coordinates, animation visuals, visibility, layers, and direct `formatted_symbol` assignments.
Wide characters use the existing width-aware renderer; caching resumes when all visible characters are single-cell.
Existing motion and animation references, paths, and scenes remain valid when caching is enabled.

Measure before enabling caching: tracking and row membership consume extra memory, and frequent changes can reduce
the benefit. Matrix enables it for canvases with at least four rows and 256 cells, where fixed-clock measurements
showed a benefit. Smaller canvases retain the default renderer. For repeatable Matrix comparisons, advance its
wall-clock-based rain phase with the same simulated clock in both runs and verify frame counts and output hashes.

Print, Pour, BouncyBalls, ErrorCorrect, SynthGrid, and Rain also enable caching automatically in measured input ranges:

| Effect | Activation requirements |
| --- | --- |
| Print | Text at least 16 columns by 4 rows, with at least 256 input characters. |
| Pour | Up/down pouring; text at least 64 by 12, with at least 768 characters and three-quarter occupancy. |
| BouncyBalls | Text at least 64 by 16, with at least 1,024 characters and three-quarter occupancy. |
| ErrorCorrect | Text at least 8 by 5, with at least 80 input characters. |
| SynthGrid | Visible canvas at least 8 by 4, including sparse text. |
| Rain | Text at least 80 by 24, with at least 1,680 characters and seven-eighths occupancy. |

These six effects require single-cell input symbols. The text-based gates also require the text bounds to fit within
the visible canvas. Occupancy is the input-character count divided by the area of the text bounds; fill and helper
characters do not contribute. These checks run before effect build and helper allocation. Later wide visual changes
still use the engine's width-aware fallback. Horizontal Pour and input shapes below these thresholds retain ordinary
rendering. Cache activation changes rendering work without changing effect options, scheduling, or random decisions.

## Spotlights illumination

Spotlights indexes authored input cells by column and row. Beam selection uses the original floating ellipse spans,
including wide continuation cells and input spaces with parsed colors. Empty fill cells are excluded from the index;
the effect does not need to materialize them. Input coordinates and symbols remain fixed throughout illumination.

Brightness results use exact color-pair and factor keys in a separate 4,096-entry cache for each iterator. Both initial
dim colors and beam falloff use this bounded cache. Factors are not quantized, and cached colors remain immutable.

The effect also reuses an unchanged current visual. Its appearance snapshot includes all visual instance fields and
the animation color policy. Direct style or formatted-symbol edits, visual replacement, and policy changes cause the
effect to reapply the intended appearance. In `always` input-color mode, Spotlights uses the shared
`Animation.set_appearance_if_changed()` helper to compare effective colors after input overrides. Other modes retain
the local appearance cache. Callers should not rely on receiving a new visual object each frame. The shared
`set_appearance()` method still creates a fresh visual on every call.

Spotlights retains the default terminal renderer. Row caching offered little additional benefit after illumination
optimization and regressed the tested Unicode input.

Local paired iterator measurements against the implementation before these changes used seven samples, two warmups,
and seed 1337, without terminal printing or frame-rate sleeps. Mean total times (build plus rendering) were:

| Input preset | Before (s) | After (s) | Reduction |
| --- | ---: | ---: | ---: |
| medium | 0.08475 | 0.04139 | 51.2% |
| generated (dense 80-by-24) | 2.30201 | 0.94837 | 58.8% |
| sparse | 0.29153 | 0.01922 | 93.4% |
| unicode | 0.10883 | 0.05014 | 53.9% |
| tall | 1.08830 | 0.37138 | 65.9% |

All paired frame-count and output-length arrays matched. Full-frame hashes also matched across seeded shape, color,
and effect-option comparisons. A separate fresh-process `tracemalloc` sample for dense input at seed 1337 reduced peak
Python allocation from 25.46 MB to 8.27 MB (67.5%); build peak increased from 4.43 MB to 5.12 MB. These are local timing
and traced-allocation results, not RSS measurements or universal performance guarantees.

## Opt-in appearance reuse

`Animation.set_appearance_if_changed(symbol=None, colors=None)` follows the ordinary setter's symbol defaults,
color overrides, and width tracking. It reuses its last visual when the effective request, color policy, visual
identity, and all visual instance fields remain unchanged. Scene stepping, an ordinary setter call, or direct
style, color-code, width, or formatted-symbol edits force the next helper call to reapply the requested appearance.
The helper does not stop an active scene from overwriting that appearance on its next step.

The snapshot is allocated lazily for each animation using the helper. It retains one visual and field snapshot;
visuals are not shared across characters. `Animation.set_appearance()` remains available when callers require a fresh
visual on every call. Effects should opt in only after measuring their workloads: comparing and retaining snapshots
can cost more than it saves when effective appearances change frequently.

Overflow row coloring and Spotlights opt in only when `existing_color_handling="always"`. For input-derived
characters, the helper ignores requested colors in the comparison because parsed input colors override them.
Helper characters without input-color ownership still compare the requested colors. Other color modes retain their
previous appearance paths.

Local paired iterator benchmarks used seven samples, two warmups, and seeds 1339–1345 after warmup seeds 1337–1338.
There was no terminal printing or frame-rate sleeping. Dense `always` mode results were:

| Effect | Before (s) | After (s) | Reduction |
| --- | ---: | ---: | ---: |
| Overflow | 0.37166 | 0.25213 | 32.2% |
| Spotlights | 0.93603 | 0.77500 | 17.2% |

Frame counts and output lengths matched in all eight timing comparisons. Full-frame hashes matched in 100 seeded
comparisons across medium, Unicode, colored, sparse, and dense input, all color-handling modes, and no-color/XTerm rendering.
A separate fresh-process dense `always` sample at seed 1337 changed Overflow peak traced Python allocation
from 16.81 MB to 20.43 MB (+21.6%).
A separate fresh-process dense `always` sample at seed 1337 changed Spotlights peak traced Python allocation
from 8.07 MB to 8.01 MB (-0.8%).
Overflow retains snapshots for moving rows, trading memory for reduced repeated visual construction. These are local
timings and traced Python allocations, not RSS measurements or universal speed guarantees.

## Motion activation distances

`Motion.activate_path()` calculates straight-line origin distances with the same terminal-scaled `math.hypot`
arithmetic as the geometry helper, avoiding its coordinate-key hashing. Bézier activation retains the shared
curve-distance cache. Every activation still constructs a fresh origin waypoint and segment, resets playback,
and dispatches events in the same order. No per-path distance cache is allocated.

Local production verification on 2026-10-03 used seven paired samples, two warmups, and measured seeds 1339–1345,
without terminal printing or frame-rate sleeps. The baseline method was snapshotted before editing; all other engine
and effect code was shared. Geometry caches were cleared before each iteration, then warmed by its own build.

| Rings input | Before total (s) | After total (s) | Reduction |
| --- | ---: | ---: | ---: |
| generated | 1.41773 | 1.38221 | 2.5% |
| medium | 0.10063 | 0.09800 | 2.6% |
| tall | 0.42941 | 0.41499 | 3.4% |
| wide | 0.01797 | 0.01755 | 2.3% |
| sparse | 0.00674 | 0.00657 | 2.4% |
| unicode | 0.08290 | 0.08093 | 2.4% |

All per-seed frame-count and output-length arrays matched, as did 44 seeded full-frame comparisons across Rings
shapes, colors, offsets and configurations, and six control effects. Separate dense seed-1337 traced allocation
samples measured 110.56 MB before and 111.67 MB after (+1.0%).
These are local iterator timings and traced Python allocations, not RSS measurements or universal speed guarantees.

## Opt-in eased-scene schedules

`Animation.new_scene(cache_easing=True)` or `Scene(..., cache_easing=True)` reuses immutable frame-index
schedules for scenes with matching built-in easing functions and duration boundaries. Frames, visuals,
playback counters and lifecycle events remain independently owned. Only Waves opts in by default.
Custom easing callables, scenes beyond the 4096-tick entry limit, and motion-synced scenes retain their
ordinary playback calculations. The engine keeps at most 32 schedules; weak scene references allow
entries to be released on eviction and lazily reacquired during playback. Easing changes or appended
frames select a new schedule; resetting/looping reuses the existing layout.

Use the helper after measuring repeated layouts. Many unique schedules or short/cancelled playback can
pay for precomputation without enough reuse. Opting in does not cache arbitrary callback results or share
mutable animation state. Manually changed out-of-range cursors retain ordinary easing/clamping behavior.

Local production comparisons used the repository harness with actual pre-change source in isolated
workers: seven samples, two warmups, seeds 1339–1345, serial rotating arms, GC before each run and cold
schedule caches. Defaults, no terminal printing and no frame-rate sleeping were retained. The baseline
already contains Waves' effect-local construction optimizations. Results measure this engine feature alone.

| Input / color mode | Before total s | After total s | Iteration reduction | Total reduction |
| --- | ---: | ---: | ---: | ---: |
| generated / ignore | 1.849471 | 1.644767 | 19.7% | 11.1% |
| medium / ignore | 0.068867 | 0.061437 | 18.5% | 10.8% |
| unicode / ignore | 0.042426 | 0.038307 | 15.9% | 9.7% |
| generated / always | 1.733739 | 1.529323 | 19.4% | 11.8% |
| generated / dynamic | 1.630213 | 1.423876 | 22.5% | 12.7% |
| sparse / dynamic | 0.002995 | 0.002934 | 3.6% | 2.1% |

All timing and separate memory frame/output-count arrays matched. All 68 full-frame SHA256/final-state
comparisons matched across Waves shape/color/easing/configuration cases and BinaryPath/Expand controls.
A fresh-process dense seed-1339 trace changed peak Python allocation from 154.208 MiB to
154.402 MiB (+0.126%, about 0.19 MiB). Memory tracing ran outside timing.
BinaryPath/Expand kept caching disabled; their small total-time variations (+0.9%/-1.8%) did not establish
a meaningful change. Thunderstorm remains disabled and has no timing claim because its output is not
reproducible under the existing benchmark. These are local measurements, not universal guarantees or RSS.
