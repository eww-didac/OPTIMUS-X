"""Optimus X — Windows system optimizer.

Entry point:  python main.py
"""

from __future__ import annotations

import sys


def _configure_runtime() -> None:
    """Tune the interpreter for a UI thread that shares work with workers.

    Telemetry, registry scans and process listings run on background threads.
    The default 5 ms GIL switch interval lets those bursts hold up Tk long
    enough to be visible while a page is opening; a shorter interval keeps
    input and redraws responsive without meaningfully increasing overhead.
    """

    try:
        sys.setswitchinterval(0.002)
    except Exception:
        pass


def main() -> None:
    _configure_runtime()
    # Importing the application builds the widget toolkit and starts the
    # telemetry service, so keep it inside main() instead of doing that work
    # when this module is imported by tooling.
    from app.application import OptimusXApp

    app = OptimusXApp()
    app.mainloop()


if __name__ == "__main__":
    main()
