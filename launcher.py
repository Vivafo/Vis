"""Simple Tk launcher for the stair and baluster tools."""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from typing import Literal, Optional


Choice = Optional[Literal["escalier", "balustre_marche", "balustre_gc"]]


def _ensure_pythonpath() -> None:
    """Ensure the project root and its parent are on sys.path."""
    project_root = Path(__file__).resolve().parent
    parent_root = project_root.parent
    for path in (project_root, parent_root):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _launch_escalier() -> None:
    """Run the main stair calculator UI."""
    from main_app import main as escalier_main

    escalier_main()


def _launch_balustre(mode: Literal["Marche", "Garde-corps"]) -> None:
    """Open the baluster application directly in the requested mode."""
    from balustre.balustre_aff import ToggleFormApp

    app = ToggleFormApp()
    if mode == "Garde-corps":
        app.after(0, app.gc_btn.invoke)
    else:
        app.after(0, app.marche_btn.invoke)
    app.mainloop()


def main() -> None:
    """Display a small menu letting the user choose which tool to open."""
    _ensure_pythonpath()

    selection: Choice = None

    root = tk.Tk()
    root.title("Lanceur Escalier / Balustre")
    root.geometry("320x180")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(expand=True, fill="both")

    label = tk.Label(
        frame,
        text="Choisissez un module à ouvrir :",
        font=("Segoe UI", 11, "bold"),
    )
    label.pack(pady=(0, 12))

    def choose(value: Choice) -> None:
        nonlocal selection
        selection = value
        root.quit()

    tk.Button(
        frame,
        text="Escalier (application principale)",
        width=30,
        command=lambda: choose("escalier"),
    ).pack(pady=5)

    tk.Button(
        frame,
        text="Balustre - Marche",
        width=30,
        command=lambda: choose("balustre_marche"),
    ).pack(pady=5)

    tk.Button(
        frame,
        text="Balustre - Garde-corps",
        width=30,
        command=lambda: choose("balustre_gc"),
    ).pack(pady=5)

    tk.Button(
        frame,
        text="Quitter",
        width=30,
        command=lambda: choose(None),
    ).pack(pady=(12, 0))

    root.mainloop()
    root.destroy()

    if selection == "escalier":
        _launch_escalier()
    elif selection == "balustre_marche":
        _launch_balustre("Marche")
    elif selection == "balustre_gc":
        _launch_balustre("Garde-corps")


if __name__ == "__main__":
    main()
