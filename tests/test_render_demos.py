"""Cover the demo renderer's output and demo selection."""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter
from tools import render_demos

if TYPE_CHECKING:
    from pathlib import Path


def write_recording(path: Path, frames: list[str], frame_rate: int = 10) -> None:
    """Write a two-cell, two-row recording holding `frames`."""
    with RecordingWriter(path, RecordingHeader("test", 2, 2, frame_rate)) as writer:
        writer.begin_segment("test")
        for frame in frames:
            writer.write_frame(frame)


def test_render_writes_each_format_and_reports_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each requested format is drawn from one recording and named after the demo."""
    pytest.importorskip("PIL")

    def record(_demo: render_demos.Demo, path: Path) -> None:
        write_recording(path, ["ab\ncd", "ef\ngh"])

    monkeypatch.setattr(render_demos, "record", record)
    message, fingerprint = render_demos.render(
        "beams",
        render_demos.Demo(effect="beams"),
        tmp_path,
        render_demos.RenderOptions(formats=("gif", "webp")),
    )
    assert (tmp_path / "beams_demo.gif").read_bytes().startswith(b"GIF89a")
    assert (tmp_path / "beams_demo.webp").read_bytes()[8:12] == b"WEBP"
    assert message.startswith("beams: gif ")
    assert ", webp " in message
    assert len(fingerprint) == 64


def test_every_builtin_effect_has_a_demo() -> None:
    """Demos default to each built-in effect with its default options."""
    demos = render_demos.demos()
    assert list(demos) == render_demos.builtin_effects()
    assert demos["beams"] == render_demos.Demo(effect="beams")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("webp", ["webp"]), ("gif, webp", ["gif", "webp"])],
)
def test_formats_parse(value: str, expected: list[str]) -> None:
    """Formats are a comma-separated subset of the supported formats."""
    assert render_demos.parse_formats(value) == expected


@pytest.mark.parametrize("value", ["", "png", "webp,mp4"])
def test_formats_reject_unknown(value: str) -> None:
    """Empty and unsupported formats are rejected."""
    with pytest.raises(argparse.ArgumentTypeError):
        render_demos.parse_formats(value)


def test_fingerprint_follows_frames_and_render_settings(tmp_path: Path) -> None:
    """A demo's fingerprint changes when its frames or how they're drawn change, and only then."""
    demo = render_demos.Demo(effect="beams")
    first, same, changed = tmp_path / "first.tterec", tmp_path / "same.tterec", tmp_path / "changed.tterec"
    write_recording(first, ["ab\ncd", "ef\ngh"])
    write_recording(same, ["ab\ncd", "ef\ngh"])
    write_recording(changed, ["ab\ncd", "ef\ngx"])
    fingerprint = render_demos.fingerprint(first, demo, 60)
    assert render_demos.fingerprint(same, demo, 60) == fingerprint
    assert render_demos.fingerprint(changed, demo, 60) != fingerprint
    assert render_demos.fingerprint(first, render_demos.Demo(effect="beams", end_hold=1.0), 60) != fingerprint


def test_manifest_keeps_other_demos(tmp_path: Path) -> None:
    """Rendering some demos replaces their fingerprints and keeps the rest."""
    render_demos.write_manifest(tmp_path, {"beams": "a", "burn": "b"})
    render_demos.write_manifest(tmp_path, {"burn": "c"})
    assert render_demos.read_manifest(tmp_path) == {"beams": "a", "burn": "c"}


@pytest.mark.parametrize(
    ("formats", "manifest"),
    [("webp", {"beams": "fingerprint of beams"}), ("gif", {})],
)
def test_main_renders_each_demo_once_and_records_webp_fingerprints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    formats: str,
    manifest: dict[str, str],
) -> None:
    """A demo named twice renders once, and only WebP renders, which are committed, update the manifest."""
    pytest.importorskip("PIL")
    rendered: list[str] = []

    def try_render(name: str, *_: object) -> tuple[str, str]:
        rendered.append(name)
        return name, f"fingerprint of {name}"

    monkeypatch.setattr(render_demos, "try_render", try_render)
    monkeypatch.setattr(render_demos, "ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(sys, "argv", ["render_demos", "beams", "beams", "--formats", formats, "--out", str(tmp_path)])
    assert render_demos.main() == 0
    assert rendered == ["beams"]
    assert render_demos.read_manifest(tmp_path) == manifest
