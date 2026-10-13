"""Keep the effects showroom argument blocks in sync with the built-in CLI parsers."""

from __future__ import annotations

import pytest

from tools import generate_showroom


def test_showroom_matches_cli_parsers() -> None:
    """The committed showroom equals a fresh render; run tools/generate_showroom.py after changing effect options."""
    source = generate_showroom.SHOWROOM_PATH.read_text(encoding="utf-8")
    assert generate_showroom.render_showroom(source, generate_showroom.effect_parsers()) == source


def test_showroom_requires_every_effect_section() -> None:
    """A built-in effect without a showroom section is reported instead of silently skipped."""
    source = generate_showroom.SHOWROOM_PATH.read_text(encoding="utf-8").replace("## Wipe\n", "## Removed\n")
    with pytest.raises(ValueError, match="missing: wipe; unknown: removed"):
        generate_showroom.render_showroom(source, generate_showroom.effect_parsers())


def test_epilog_separates_example_from_indented_notes() -> None:
    """Indented shared notes are dedented and the example line is set apart."""
    assert generate_showroom.render_epilog("    Notes\n        detail\nExample: tte demo") == [
        "Notes",
        "    detail",
        "",
        "Example: tte demo",
    ]
