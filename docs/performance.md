# Performance Testing

This page is for contributors. The benchmark commands run from a repository checkout set up as described in
[CONTRIBUTING.md](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/CONTRIBUTING.md).

Use `tools/perf/benchmark_effects.py` for repeatable effect performance checks. The harness uses only the Python
standard library, disables frame-rate sleeps, renders through the library iterator API, and avoids terminal output.

## Benchmark Harness

### Baseline

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

### Candidate

After making a focused change and running the relevant functional checks, rerun the same benchmark arguments:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --effect wipe \
  --input-preset medium \
  --json-out /tmp/tte-candidate.json
```

Compare the two reports:

```bash
./.venv/bin/python tools/perf/benchmark_effects.py \
  --compare /tmp/tte-baseline.json /tmp/tte-candidate.json
```

The comparison is advisory by default. Report build, render, and total mean deltas along with frame-count or output-size
changes, but do not treat regressions as failures unless a task explicitly sets a threshold.

### Profiling

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

## Reporting a Change

Put the measurements for a performance change in its PR description, not on this page. A useful report includes:

- **Method:** the harness arguments, samples, warmups, and seeds, and what the baseline was (for example, the parent
  commit with all other code shared).
- **Timing:** before and after mean totals for each input preset that matters to the change, with build and iteration
  split out when they move in different directions.
- **Memory:** peak traced allocation from a separate `--memory` run, since tracing distorts timings.
- **Output parity:** frame counts, output lengths, and full-frame hashes matching across seeds, input shapes, color
  modes, and affected effect options. A speedup that changes output is a behavior change.
- **Controls:** unaffected effects measured alongside, so noise is not mistaken for a gain.

These are local iterator timings and traced Python allocations, not RSS measurements or guarantees for other machines.
Say so instead of rounding small deltas into claims.

## Recorded Optimizations

Optimizations made before this convention recorded their measurements here. The table summarizes them; the
[archived version of this page](https://github.com/ChrisBuilds/terminaltexteffects/blob/ccde68a/docs/performance.md#measured-optimizations)
keeps the full method, per-preset tables, and parity checks. API usage lives in the linked reference pages.

| Optimization | Used by | Result (dense input unless noted) | Reference |
| --- | --- | --- | --- |
| Opt-in row caching | Matrix, Print, Pour, BouncyBalls, ErrorCorrect, SynthGrid, Rain | Enabled only within measured input ranges | [Terminal](engine/terminal/terminal.md#row-caching) |
| Spotlights illumination index and brightness cache | Spotlights | 51–93% faster total across presets; peak allocation 25.5 MB → 8.3 MB | — |
| Opt-in appearance reuse | Overflow, Spotlights (`always` color mode) | Overflow 32% and Spotlights 17% faster; Overflow peak allocation +22% | [Animation](engine/animation/animation.md#appearance-reuse) |
| Straight-line motion activation distances | All path-based effects | Rings about 2–3% faster across presets | — |
| Opt-in eased-scene schedules | Waves | 10–13% faster total on most presets | [Scene](engine/animation/scene.md#eased-scene-schedules) |
| Opt-in encoded appearance construction | Waves | Peak allocation −10% to −20%; total time within ±3% | [Scene](engine/animation/scene.md#encoded-appearance-reuse) |
