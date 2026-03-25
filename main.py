from __future__ import annotations

import sys

from bulletin_app.cli import main as cli_main
from bulletin_app.gui import launch_gui


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(cli_main())
    launch_gui()
