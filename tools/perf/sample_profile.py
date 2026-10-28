"""Run Python 3.15's `profiling.sampling` CLI, dropping samples the binary writer cannot encode.

`python -m profiling.sampling run --binary` ends the whole recording when a sampled frame has a
file or function name with lone surrogates: the binary writer encodes names as strict UTF-8 and
raises `UnicodeEncodeError` (python/cpython#160601). This wrapper takes the same arguments as
`python -m profiling.sampling`, but drops such a sample instead, as the profiler already does for
samples it cannot decode. The sample is dropped before it reaches the writer: once a write fails, the
writer marks itself broken and refuses every later sample with `ValueError: Writer is broken`.

The first distinct unencodable names and the number of dropped samples go to stderr. Remove this wrapper
once the Python 3.15 used for profiling includes the upstream fix.
"""

from __future__ import annotations

import importlib
import re
import sys
from typing import Any

DROPPED_MESSAGE = "sample_profile: dropped {count} sample(s) with names the binary writer cannot encode"
MAX_REPORTED_NAMES = 5
MAX_NAME_LENGTH = 300
# Lone surrogates are the only code points strict UTF-8 cannot encode.
SURROGATE = re.compile("[\ud800-\udfff]")


def _unencodable_names(stack_frames: Any) -> list[str]:
    """Return the file and function names in `stack_frames` that strict UTF-8 cannot encode."""
    names: list[str] = []
    for interpreter in stack_frames:
        for thread in interpreter.threads:
            for frame in thread.frame_info:
                names.extend(
                    name for name in (frame.filename, frame.funcname) if not name.isascii() and SURROGATE.search(name)
                )
    return names


def _install() -> list[int]:
    """Patch `BinaryCollector.collect` to drop unencodable samples unwritten; return the dropped-sample counter."""
    # Imported by name: `profiling.sampling` is new in Python 3.15.
    binary_collector = importlib.import_module("profiling.sampling.binary_collector")

    dropped = [0]
    reported: set[str] = set()
    collect = binary_collector.BinaryCollector.collect

    def collect_encodable(self: Any, stack_frames: Any, timestamp_us: int | None = None) -> None:
        unencodable = _unencodable_names(stack_frames)
        if not unencodable:
            collect(self, stack_frames, timestamp_us)
            return
        dropped[0] += 1
        for name in unencodable:
            if name not in reported and len(reported) < MAX_REPORTED_NAMES:
                reported.add(name)
                print(f"sample_profile: unencodable name {name[:MAX_NAME_LENGTH]!a}", file=sys.stderr)

    binary_collector.BinaryCollector.collect = collect_encodable
    return dropped


def main() -> int:
    """Run the profiler CLI with the patched collector."""
    dropped = _install()
    cli = importlib.import_module("profiling.sampling.cli")

    sys.argv[0] = "python -m profiling.sampling"
    try:
        cli.main()
    finally:
        if dropped[0]:
            print(DROPPED_MESSAGE.format(count=dropped[0]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
