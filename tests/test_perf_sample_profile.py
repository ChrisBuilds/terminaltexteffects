"""Tests for the sampling-profiler wrapper that drops unencodable samples."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

import pytest

from tools.perf import sample_profile


def _sample(*names: tuple[str, str]) -> list[SimpleNamespace]:
    """Build one interpreter with one thread whose frames have the given (filename, funcname) pairs."""
    frames = [SimpleNamespace(filename=filename, funcname=funcname) for filename, funcname in names]
    return [SimpleNamespace(threads=[SimpleNamespace(frame_info=frames)])]


def test_unencodable_names_lists_only_names_with_lone_surrogates() -> None:
    """Valid non-ASCII names pass; file and function names with lone surrogates are listed."""
    sample = _sample(("effect.py", "build"), ("b\udb31d.py", "ok"), ("café.py", "spin\uda5e"))

    assert sample_profile._unencodable_names(sample) == ["b\udb31d.py", "spin\uda5e"]


@pytest.mark.skipif(sys.version_info < (3, 15), reason="profiling.sampling is new in Python 3.15")
def test_patched_collector_drops_unencodable_samples(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A sample the writer cannot encode never reaches it; it is counted, and its new names are reported once."""
    binary_collector = importlib.import_module("profiling.sampling.binary_collector")

    written: list[object] = []
    broken = False

    def collect(_self: object, stack_frames: list[SimpleNamespace], _timestamp_us: int | None = None) -> None:
        # Like CPython's writer, refuse every sample after a failed one.
        nonlocal broken
        if broken:
            msg = "Writer is broken"
            raise ValueError(msg)
        if sample_profile._unencodable_names(stack_frames):
            broken = True
            "\udb31".encode()
        written.append(stack_frames)

    monkeypatch.setattr(binary_collector.BinaryCollector, "collect", collect)
    dropped = sample_profile._install()
    good = _sample(("effect.py", "build"))
    bad = _sample(("effect.py", "spin\udb31"))

    for stack_frames in (good, bad, bad, good):
        binary_collector.BinaryCollector.collect(object(), stack_frames)

    assert written == [good, good]
    assert dropped == [2]
    assert capsys.readouterr().err.splitlines() == ["sample_profile: unencodable name 'spin\\udb31'"]
