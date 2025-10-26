"""
Composants Tkinter réutilisables pour les formulaires du module balustre.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable, Sequence

from balustre.theme import ESC_INPUT_BG

DENOMINATOR_VALUES: Sequence[str] = ("2", "4", "8", "16", "32", "64")


def create_column_headers(
    parent: tk.Widget,
    titles: Iterable[str],
    *,
    font: tuple[str, int, str],
    fg: str,
    bg: str,
    start_column: int = 1,
    width: int = 7,
) -> None:
    """
    Affiche les en-têtes de colonnes pour une grille de mesures.
    """
    for index, title in enumerate(titles, start=start_column):
        tk.Label(
            parent,
            text=title,
            font=font,
            bg=bg,
            fg=fg,
            width=width,
            anchor="center",
        ).grid(row=0, column=index, padx=1, pady=(0, 3))


def build_measurement_row(
    parent: tk.Widget,
    *,
    row_index: int,
    label_text: str,
    label_font: tuple[str, int],
    entry_font: tuple[str, int],
    label_fg: str,
    label_bg: str,
    label_width: int = 12,
    specs: Sequence[dict],
    validatecommand=None,
) -> list[tk.Widget]:
    """
    Crée une ligne de saisie comprenant un label et une série d'entrées/combobox.

    Chaque élément de `specs` doit contenir au minimum la clé `type` (entry/combobox).
    """
    tk.Label(
        parent,
        text=label_text,
        font=label_font,
        bg=label_bg,
        fg=label_fg,
        width=label_width,
        anchor="w",
    ).grid(row=row_index, column=0, padx=(2, 6), sticky="w")

    widgets: list[tk.Widget] = []
    for offset, spec in enumerate(specs, start=1):
        kind = spec.get("type", "entry")
        width = spec.get("width", 4)
        padx = spec.get("padx", 1)
        pady = spec.get("pady", (0, 0))
        justify = spec.get("justify", "center")

        if kind == "combobox":
            widget = ttk.Combobox(
                parent,
                width=width,
                values=spec.get("values", ()),
                state=spec.get("state", "readonly"),
                font=entry_font,
                justify=justify,
            )
            default = spec.get("default")
            if default is not None:
                widget.set(default)
        else:
            widget = tk.Entry(
                parent,
                width=width,
                font=entry_font,
                justify=justify,
                bg=spec.get("bg", ESC_INPUT_BG),
                bd=1,
                relief="solid",
            )
            use_validate = spec.get("use_validate", True)
            if validatecommand and use_validate:
                widget.configure(validate="key", validatecommand=validatecommand)

        widget.grid(row=row_index, column=offset, padx=padx, pady=pady)
        widgets.append(widget)

    return widgets


__all__ = ["DENOMINATOR_VALUES", "create_column_headers", "build_measurement_row"]
