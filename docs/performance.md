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
