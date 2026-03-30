from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Return the runtime root for local runs and packaged builds."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return app_root() / "assets"


def templates_dir() -> Path:
    return app_root() / "templates"


def thumbnails_dir() -> Path:
    return app_root() / "thumbnails"
