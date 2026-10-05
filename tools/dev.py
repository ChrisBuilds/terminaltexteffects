"""Run the CLI with this checkout's development effects enabled."""

from __future__ import annotations

import os
from pathlib import Path

from terminaltexteffects.__main__ import main


def run() -> None:
    """Select the development directory and forward CLI arguments unchanged."""
    os.environ["TTE_DEV_EFFECTS_DIR"] = str(Path(__file__).resolve().parents[1] / "dev_effects")
    main()


if __name__ == "__main__":
    run()
