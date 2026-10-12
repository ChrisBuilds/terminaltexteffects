"""MkDocs hook that shows pending changelog fragments on the changelog page."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import changelog  # noqa: E402 - the project root must be importable first.


def on_page_markdown(markdown: str, page: Any, **_kwargs: Any) -> str:
    """Replace the changelog page with `CHANGELOG.md` plus the rendered Unreleased section."""
    if page.file.src_uri != "changelog.md":
        return markdown
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return changelog.insert_preview(text, changelog.render_preview(ROOT))
