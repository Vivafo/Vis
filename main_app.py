"""Application bootstrap for the Modern Stair Calculator UI."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_pythonpath() -> None:
    """Ensure the project and its parent are on sys.path for module resolution."""
    project_root = Path(__file__).resolve().parent
    parent_root = project_root.parent
    for path in (project_root, parent_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


_ensure_pythonpath()

from escalier.controllers.app_controller import AppController
from escalier.ui.main_window import ModernStairCalculator

__all__ = ["main"]


def main() -> None:
    """Launch the Tkinter application."""
    app = ModernStairCalculator()
    controller = AppController(app)
    controller.initialize()
    app.mainloop()


if __name__ == "__main__":
    main()
