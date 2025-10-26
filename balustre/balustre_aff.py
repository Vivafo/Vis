import tkinter as tk
from tkinter import ttk

from core import calc_balustre
from core.formatting import aggregate_units_to_inches, inches_to_feet_inches_fraction
from balustre.theme import (
    ESC_ACCENT,
    ESC_ACCENT_DARK,
    ESC_FOND,
    ESC_FOND_SECONDARY,
    ESC_TEXTE,
)
from balustre.widgets_shared import (
    DENOMINATOR_VALUES,
    build_measurement_row,
    create_column_headers,
)

_DENOMINATOR_INT_VALUES = tuple(int(value) for value in DENOMINATOR_VALUES)

# -----------------------------
# Application
# -----------------------------
class ToggleFormApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calcul Marche / Garde-corps")
        self.configure(bg=ESC_FOND)
        self.geometry("620x320+960+40")
        self.resizable(False, False)

        font_label = ("Segoe UI", 9)
        font_entry = ("Segoe UI", 10)

        # Onglets (boutons)
        btn_frame = tk.Frame(self, bg=ESC_FOND)
        btn_frame.pack(pady=8)
        self.mode_var = tk.StringVar(value="Marche")

        def select_mode(mode):
            self.mode_var.set(mode)
            self.show_box(mode)
            self.marche_btn.configure(
                bg=ESC_ACCENT if mode == "Marche" else ESC_FOND,
                fg=ESC_TEXTE if mode == "Marche" else ESC_ACCENT,
            )
            self.gc_btn.configure(
                bg=ESC_ACCENT if mode == "Garde-corps" else ESC_FOND,
                fg=ESC_TEXTE if mode == "Garde-corps" else ESC_ACCENT,
            )
            self.result_var.set("")

        self.marche_btn = tk.Button(
            btn_frame, text="Marche", font=font_label,
            width=13, bg=ESC_ACCENT, fg=ESC_TEXTE, bd=0, relief="flat",
            activebackground=ESC_ACCENT_DARK,
            command=lambda: select_mode("Marche")
        )
        self.gc_btn = tk.Button(
            btn_frame, text="Garde-corps", font=font_label,
            width=13, bg=ESC_FOND, fg=ESC_ACCENT, bd=0, relief="flat",
            activebackground=ESC_ACCENT_DARK,
            command=lambda: select_mode("Garde-corps")
        )
        self.marche_btn.pack(side="left", padx=(0, 5))
        self.gc_btn.pack(side="left", padx=(5, 0))

        # Sélecteur de fraction (affichage)
        frac_frame = tk.Frame(self, bg=ESC_FOND)
        frac_frame.pack(fill="x", padx=18, pady=(2, 1))
        tk.Label(
            frac_frame, text="Fraction (affichage) :", font=("Segoe UI", 9, "bold"),
            bg=ESC_FOND, fg=ESC_ACCENT
        ).pack(side="left", padx=(0, 4))
        self.frac_var = tk.StringVar(value="1/16")
        self.frac_cb = ttk.Combobox(
            frac_frame, textvariable=self.frac_var,
            values=["1/4", "1/8", "1/16", "1/32", "1/64"],
            width=5, state="readonly", font=font_entry
        )
        self.frac_cb.pack(side="left", padx=(1, 0))

        # Zone de formulaires
        self.box_frame = tk.Frame(self, bg=ESC_FOND)
        self.box_frame.pack(padx=7, pady=(8, 2), fill="both", expand=True)
        self.forms = {}
        self.create_forms(font_label, font_entry)
        self.show_box("Marche")

        # Boutons actions
        calc_frame = tk.Frame(self, bg=ESC_FOND)
        calc_frame.pack(fill="x")
        self.calc_btn = tk.Button(
            calc_frame, text="Calculer", font=("Segoe UI", 10, "bold"),
            bg=ESC_ACCENT, fg=ESC_TEXTE, relief="flat",
            activebackground=ESC_ACCENT_DARK, borderwidth=2, height=1, cursor="hand2",
            command=self.calculer
        )
        self.calc_btn.pack(pady=(5, 2), anchor="center")

        # Zone de résultat
        self.result_var = tk.StringVar(value="")
        self.result_lbl = tk.Label(
            self, textvariable=self.result_var, font=("Segoe UI", 9),
            bg=ESC_FOND_SECONDARY, fg=ESC_TEXTE, anchor="w", justify="left"
        )
        self.result_lbl.pack(fill="x", padx=8, pady=(4, 0))
        self._last_payload = None

    # ---- UI builders ----
    def validate_4char(self, P):
        return len(P) <= 4

    def create_forms(self, font_label, font_entry):
        vcmd = (self.register(self.validate_4char), '%P')

        # ---------- Forme "Marche" ----------
        form1 = tk.Frame(self.box_frame, bg=ESC_FOND)
        labels = ("Long. giron", "Balustre", "Esp. max")
        col_titles = ("Pouce", "Num", "Den", "cm", "mm")
        create_column_headers(
            form1,
            col_titles,
            font=("Segoe UI", 8, "bold"),
            fg=ESC_ACCENT,
            bg=ESC_FOND,
        )
        self.entries_marche = []
        marche_specs = (
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
            {"type": "combobox", "width": 5, "values": DENOMINATOR_VALUES, "default": "8"},
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
        )
        for idx, label in enumerate(labels, start=1):
            widgets = build_measurement_row(
                form1,
                row_index=idx,
                label_text=label,
                label_font=font_label,
                entry_font=font_entry,
                label_fg=ESC_ACCENT,
                label_bg=ESC_FOND,
                specs=marche_specs,
                validatecommand=vcmd,
            )
            self.entries_marche.append(widgets)
        self.forms["Marche"] = form1

        # ---------- Forme "Garde-corps" ----------
        form2 = tk.Frame(self.box_frame, bg=ESC_FOND)
        labels_gc = ("Long. GC", "Largeur balustre", "Ouverture max")
        col_titles_gc = ("Pied", "Pouce", "Num", "Den", "m", "cm", "mm")
        create_column_headers(
            form2,
            col_titles_gc,
            font=("Segoe UI", 8, "bold"),
            fg=ESC_ACCENT,
            bg=ESC_FOND,
        )
        self.entries_gc = []
        gc_specs = (
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
            {"type": "combobox", "width": 5, "values": DENOMINATOR_VALUES, "default": "8"},
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
            {"type": "entry", "width": 4},
        )
        for idx, label in enumerate(labels_gc, start=1):
            widgets = build_measurement_row(
                form2,
                row_index=idx,
                label_text=label,
                label_font=font_label,
                entry_font=font_entry,
                label_fg=ESC_ACCENT,
                label_bg=ESC_FOND,
                label_width=16,
                specs=gc_specs,
                validatecommand=vcmd,
            )
            self.entries_gc.append(widgets)
        self.forms["Garde-corps"] = form2

    def show_box(self, mode):
        for f in self.forms.values():
            f.pack_forget()
        self.forms[mode].pack(expand=True)

    # ---- Parsing/validation fractions ----
    def _parse_num(self, s) -> int:
        try:
            return int(str(s).strip())
        except Exception:
            return 0

    def _parse_den(self, s) -> int:
        try:
            d = int(str(s).strip())
            return d if d in _DENOMINATOR_INT_VALUES else 8
        except Exception:
            return 8

    def _frac_value(self, num_str, den_str) -> float:
        n = self._parse_num(num_str)
        d = self._parse_den(den_str)
        if n < 0 or n >= d:
            raise ValueError(f"Numérateur {n} invalide pour dénominateur {d} (attendu 0..{d-1}).")
        return n / d

    # ---- Calcul ----
    def calculer(self):
        mode = self.mode_var.get()
        # Dénominateur d'affichage (combo globale)
        try:
            denom_display = int(self.frac_var.get().split("/")[-1]) if "/" in self.frac_var.get() else 16
        except Exception:
            denom_display = 16

        try:
            if mode == "Marche":
                vals = []
                labels = ["Longueur giron", "Largeur balustre", "Espacement max"]
                for i in range(3):
                    pouce = self.entries_marche[i][0].get()
                    num   = self.entries_marche[i][1].get()
                    den   = self.entries_marche[i][2].get()
                    cm    = self.entries_marche[i][3].get()
                    mm    = self.entries_marche[i][4].get()

                    frac_val = self._frac_value(num, den)  # contrôle logique n/d
                    val = aggregate_units_to_inches(
                        pouces=pouce,
                        fraction=frac_val,
                        cm=cm,
                        mm=mm,
                    )
                    if val is None:
                        self.result_var.set(f"Saisie invalide dans {labels[i]} (ligne {i+1})")
                        return
                    vals.append(val)
                gironin, balustrelargeurin, espacementmaximumin = vals
                # denom_max pour le core = précision fractionnelle de sortie
                result = calc_balustre.marche_centers(gironin, balustrelargeurin, espacementmaximumin, denom_display)

            else:
                vals = []
                labels = ["Longueur GC", "Largeur balustre", "Ouverture max"]
                for i in range(3):
                    pied  = self.entries_gc[i][0].get()
                    pouce = self.entries_gc[i][1].get()
                    num   = self.entries_gc[i][2].get()
                    den   = self.entries_gc[i][3].get()
                    metre = self.entries_gc[i][4].get()
                    cm    = self.entries_gc[i][5].get()
                    mm    = self.entries_gc[i][6].get()

                    frac_val = self._frac_value(num, den)  # contrôle logique n/d
                    val = aggregate_units_to_inches(
                        pieds=pied,
                        pouces=pouce,
                        fraction=frac_val,
                        metres=metre,
                        cm=cm,
                        mm=mm,
                    )
                    if val is None:
                        self.result_var.set(f"Saisie invalide dans {labels[i]} (ligne {i+1})")
                        return
                    vals.append(val)
                Lin, Win, Omaxin = vals
                result = calc_balustre.gc_equal_gaps(Lin, Win, Omaxin, denom_display)

            # Rapport formaté
            txt, rows = self._build_report(mode, result, denom_display)
            self._last_payload = {"mode": mode, "denom": denom_display, "result": result, "rows": rows}
            self.result_var.set(txt)

        except Exception as e:
            self.result_var.set(f"Erreur : {e}")

    # ---- Rapport lisible ----
    def _build_report(self, mode: str, out: dict, denom: int):
        lines, rows = [], []
        dec = (out or {}).get("display_decimal_in", {})
        ver = (out or {}).get("verification", {})
        def ok(x): return "PASS" if x else "FAIL"

        if mode == "Garde-corps":
            o = (out.get("outputs", {}) or {})
            N, g, s = o.get("N"), o.get("g_in"), o.get("s_in")
            centers = o.get("centers_in", [])
            lines.append("[GC] Répartition balustres (equal gaps)")
            lines.append(f"N balustres : {N}")
            lines.append(f"Ouverture g : {inches_to_feet_inches_fraction(g or 0, denom=denom)}  ({(dec.get('g_in') or round((g or 0),4))} in)")
            lines.append(f"Pas centre s : {inches_to_feet_inches_fraction(s or 0, denom=denom)}")
            lines.append("Centres :")
            for i, c in enumerate(centers, 1):
                rows.append([i, c])
                lines.append(f"  #{i:02d}  {inches_to_feet_inches_fraction(c, denom=denom)}")
            if ver:
                lines.append("Contrôles :")
                lines.append(f"  g ≤ O_max : {ok(ver.get('g_in_leq_Omax', False))}")
                lines.append(f"  Bord gauche : {ok(ver.get('left_edge_ok', False))}")
                lines.append(f"  Bord droit  : {ok(ver.get('right_edge_ok', False))}")
        else:  # Marche
            o = (out.get("outputs", {}) or {})
            step = o.get("step_in")
            centers = o.get("centers_in", [])
            lines.append("[Marche] Répartition balustres sur giron")
            lines.append(f"Pas centre : {inches_to_feet_inches_fraction(step or 0, denom=denom)}")
            lines.append("Centres :")
            for i, c in enumerate(centers, 1):
                rows.append([i, c])
                lines.append(f"  #{i:02d}  {inches_to_feet_inches_fraction(c, denom=denom)}")
            if ver:
                lines.append("Contrôles :")
                for k, v in ver.items():
                    lines.append(f"  {k} : {ok(bool(v))}")

        return "\n".join(lines), rows


if __name__ == "__main__":
    app = ToggleFormApp()
    app.mainloop()
