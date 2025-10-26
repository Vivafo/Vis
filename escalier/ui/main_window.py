# Module: escalier.ui.main_window

import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

MODULE_DIR = Path(__file__).resolve().parent
BASE_DIR = MODULE_DIR.parents[1]
ROOT_DIR = BASE_DIR.parent

for path in (BASE_DIR, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from escalier.utils.validators import prepare_main_inputs

__all__ = ["ModernStairCalculator"]

try:
    from core import constants
except ImportError as exc:
    raise ImportError("Impossible d'importer core.constants") from exc

try:
    from core import reporting
except ImportError as exc:
    print("ERREUR : Impossible d'importer reporting :", exc)
    reporting = None

try:
    from core import file_operations
except ImportError as exc:
    print("ERREUR : Impossible d'importer core.file_operations :", exc)
    file_operations = None

try:
    from core import formatting
except ImportError as exc:
    print("ERREUR : Impossible d'importer core.formatting :", exc)
    formatting = None

try:
    from core import calculations
except ImportError as exc:
    print("ERREUR : Impossible d'importer core.calculations :", exc)
    calculations = None

try:
    from core.preferences_dialog import PreferencesDialog
except ImportError as exc:
    raise ImportError("Impossible d'importer PreferencesDialog") from exc

constants_path = BASE_DIR / "core" / "constants.py"
if not constants_path.exists():
    print("ERREUR : Le fichier constants.py est introuvable :", constants_path)
elif getattr(constants, "DEBUG_MODE_ACTIVE", False):
    print("Chemin actuel :", BASE_DIR)
    print("Chemin PYTHONPATH :", sys.path)
    print("Fichier constants.py trouvé :", constants_path)

# --- Vérification et création du dossier et fichier de préférences ---
DEFAULTS_FILE = constants.DEFAULTS_FILE
DEFAULT_APP_PREFERENCES = constants.DEFAULT_APP_PREFERENCES

defaults_dir = os.path.dirname(DEFAULTS_FILE)
if defaults_dir:
    os.makedirs(defaults_dir, exist_ok=True)

if not os.path.exists(DEFAULTS_FILE):
    with open(DEFAULTS_FILE, 'w') as f:
        json.dump(DEFAULT_APP_PREFERENCES, f, indent=4)

class ModernStairCalculator(tk.Tk):
    """
    Classe principale de l'interface du calculateur d'escalier.
    Gère la fenêtre principale, les entrées, les résultats et les interactions.
    """

    def on_unit_change(self):
        """Callback exécuté quand on change l'unité (Pouces / Centimètres)."""
        new_unit = self.unites_var.get()
        previous_unit = getattr(self, "_current_input_unit", new_unit)
        print(f"⚙️ Unité sélectionnée : {new_unit}")

        if new_unit == previous_unit:
            self.app_preferences["unites_affichage"] = new_unit
            self._current_input_unit = new_unit
            return

        try:
            self._convert_inputs_between_units(previous_unit, new_unit)
        except Exception as exc:
            print(f"Erreur lors de la conversion des unités : {exc}")

        # Mettre à jour les préférences
        self.app_preferences["unites_affichage"] = new_unit
        self._current_input_unit = new_unit

        # Recalculer et rafraîchir l'UI
        try:
            self.recalculate_and_update_ui()
        except Exception as e:
            print(f"Erreur lors du recalcul après changement d'unité : {e}")

    def __init__(self):
        super().__init__()
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.title(f"Calculateur d'Escalier Pro v{constants.VERSION_PROGRAMME}")
        self.geometry("1200x850")
        self.minsize(900, 700)

        self._initialize_state()

        self._setup_style_definitions()
        self._create_menu()
        self._create_main_layout()
        self._bind_events()
        self.clear_messages()

    def set_controller(self, controller):
        """Attach an external controller to coordinate application logic."""
        self._controller = controller

    def _initialize_state(self):
        self._is_updating_ui = False
        self.latest_results = {}
        self.input_labels_map = {}
        self._pending_recalc_id = None
        self._last_changed_var = None
        self._recalculate_delay_ms = 200
        self._controller = None

        self.themes = {
            "light": {
                "fg": "#1f2933",
                "success": "#1b8a3c",
                "warning": "#c27c1f",
                "error": "#c0392b",
                "canvas_line": "#274472",
            }
        }
        self.current_theme = "light"

        base_preferences = DEFAULT_APP_PREFERENCES.copy()
        if file_operations and hasattr(file_operations, 'load_application_preferences'):
            try:
                loaded_prefs = file_operations.load_application_preferences()
                if isinstance(loaded_prefs, dict):
                    base_preferences.update(loaded_prefs)
            except Exception as exc:
                print("⚠️ Préférences par défaut utilisées (erreur de chargement) :", exc)
        self.app_preferences = base_preferences

        default_hcm = str(constants.HAUTEUR_CM_CONFORT_CIBLE)
        if formatting:
            try:
                default_hcm = formatting.decimal_to_fraction_str(
                    constants.HAUTEUR_CM_CONFORT_CIBLE, self.app_preferences
                )
            except Exception as exc:
                print("⚠️ Impossible de formater la hauteur CM par défaut :", exc)

        self.unites_var = tk.StringVar(
            value=self.app_preferences.get("unites_affichage", "pouces")
        )
        self.hauteur_totale_var = tk.StringVar()
        self.epaisseur_plancher_sup_var = tk.StringVar(
            value=self.app_preferences.get("default_floor_finish_thickness_upper", "0")
        )
        self.epaisseur_plancher_inf_var = tk.StringVar(
            value=self.app_preferences.get("default_floor_finish_thickness_lower", "0")
        )
        self.profondeur_tremie_ouverture_var = tk.StringVar()
        self.position_tremie_var = tk.StringVar()
        self.espace_disponible_var = tk.StringVar()
        self.nombre_marches_manuel_var = tk.StringVar(value="")
        self.nombre_cm_manuel_var = tk.StringVar(value="")
        self.giron_souhaite_var = tk.StringVar(
            value=self.app_preferences.get("default_tread_width_straight", "9 1/4")
        )
        self.hauteur_cm_souhaitee_var = tk.StringVar(value=default_hcm)

        self.tk_input_vars_dict = {
            "hauteur_totale_var": self.hauteur_totale_var,
            "hauteur_cm_souhaitee_var": self.hauteur_cm_souhaitee_var,
            "giron_souhaite_var": self.giron_souhaite_var,
            "epaisseur_plancher_sup_var": self.epaisseur_plancher_sup_var,
            "epaisseur_plancher_inf_var": self.epaisseur_plancher_inf_var,
            "profondeur_tremie_ouverture_var": self.profondeur_tremie_ouverture_var,
            "position_tremie_var": self.position_tremie_var,
            "espace_disponible_var": self.espace_disponible_var,
        }

        self._current_input_unit = self.unites_var.get()
        self._unit_sensitive_vars = [
            self.hauteur_totale_var,
            self.giron_souhaite_var,
            self.hauteur_cm_souhaitee_var,
            self.epaisseur_plancher_sup_var,
            self.epaisseur_plancher_inf_var,
            self.profondeur_tremie_ouverture_var,
            self.position_tremie_var,
            self.espace_disponible_var,
        ]

        self.conformity_status_var = tk.StringVar(value="EN ATTENTE")
        self.warnings_var = tk.StringVar(value="")
        self.hauteur_reelle_cm_res_var = tk.StringVar()
        self.giron_utilise_res_var = tk.StringVar()
        self.longueur_totale_res_var = tk.StringVar()
        self.angle_res_var = tk.StringVar()
        self.limon_res_var = tk.StringVar()
        self.echappee_res_var = tk.StringVar()
        self.longueur_min_escalier_var = tk.StringVar()

        self.hauteur_cm_message_var = tk.StringVar()
        self.giron_message_var = tk.StringVar()
        self.echappee_message_var = tk.StringVar()
        self.blondel_message_var = tk.StringVar()
        self.longueur_disponible_message_var = tk.StringVar()
        self.angle_message_var = tk.StringVar()
        self.hauteur_totale_ecart_message_var = tk.StringVar()

    def _convert_inputs_between_units(self, from_unit, to_unit):
        if not formatting or from_unit == to_unit:
            return

        factor = constants.POUCE_EN_CM
        was_updating = self._is_updating_ui
        self._is_updating_ui = True
        try:
            for var in self._unit_sensitive_vars:
                raw_value = var.get().strip()
                if not raw_value:
                    continue

                normalized_value = raw_value.replace(',', '.')
                try:
                    numeric_value = formatting.parser_fraction(normalized_value)
                except Exception:
                    continue

                if from_unit == "cm":
                    numeric_value /= factor

                if to_unit == "cm":
                    converted_value = numeric_value * factor
                    var.set(f"{converted_value:.2f}")
                else:
                    var.set(formatting.decimal_to_fraction_str(numeric_value, self.app_preferences))
        finally:
            self._is_updating_ui = was_updating

    def _setup_style_definitions(self):
        colors = self.themes[self.current_theme]
        self.style.configure("TLabelFrame", borderwidth=2, relief="groove", padding=10)
        self.style.configure("Conformity.TLabel", font=('Segoe UI', 12, 'bold'), foreground=colors["fg"])
        self.style.configure("Indicator.Green.TLabel", foreground=colors["success"], font=('Segoe UI', 9, 'bold'))
        self.style.configure("Indicator.Yellow.TLabel", foreground=colors["warning"], font=('Segoe UI', 9, 'bold'))
        self.style.configure("Indicator.Red.TLabel", foreground=colors["error"], font=('Segoe UI', 9, 'bold'))
        self.style.configure("InputControl.TFrame", padding=(4, 2))
        self.style.configure("DisplayValue.TLabel", font=('Segoe UI', 10, "bold"), foreground=colors["fg"], padding=(6, 2))

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        file_menu.add_command(label="Quitter", command=self.quit)

    def _create_main_layout(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(expand=True, fill="both", padx=10, pady=10)
        left_frame = ttk.Frame(main_pane, padding=10)
        self._create_input_frame(left_frame)
        self._create_results_frame(left_frame)
        self._create_warnings_frame(left_frame)
        main_pane.add(left_frame, weight=1)
        right_notebook = ttk.Notebook(main_pane)
        self.notebook = right_notebook
        self._create_visual_tab(right_notebook)
        self._create_report_tab(right_notebook)
        self._create_table_tab(right_notebook)
        main_pane.add(right_notebook, weight=2)
        
    def _create_input_frame(self, parent):
        input_frame = ttk.LabelFrame(parent, text="1. Entrées et Ajustements de l'Escalier")
        input_frame.pack(fill="x", pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)
        unit_frame = ttk.LabelFrame(input_frame, text="Unités")
        unit_frame.grid(row=0, column=4, rowspan=2, padx=5, pady=5, sticky="nsew")
        self.radio_pouces = ttk.Radiobutton(unit_frame, text="Pouces", variable=self.unites_var, value="pouces", command=self.on_unit_change)
        self.radio_cm = ttk.Radiobutton(unit_frame, text="Centimètres", variable=self.unites_var, value="cm", command=self.on_unit_change)
        self.radio_pouces.grid(row=0, column=0, padx=2, pady=2)
        self.radio_cm.grid(row=1, column=0, padx=2, pady=2)
        entries_main = [
            ("Hauteur totale :", "HT", self.hauteur_totale_var, False), ("Épaisseur plancher sup. :", "EPS", self.epaisseur_plancher_sup_var, False),
            ("Épaisseur plancher inf. :", "EPI", self.epaisseur_plancher_inf_var, False), ("Profondeur ouverture trémie :", "POT", self.profondeur_tremie_ouverture_var, True),
            ("Position départ trémie:", "PDT", self.position_tremie_var, True), ("Espace disponible (longueur) :", "ED", self.espace_disponible_var, True),
        ]
        row_idx = 0
        for text, shortcut, var, optional in entries_main:
            label = ttk.Label(input_frame, text=text)
            label.grid(row=row_idx, column=0, sticky="w", padx=5, pady=3)
            self.input_labels_map[shortcut] = (label, text)
            entry_frame = ttk.Frame(input_frame)
            entry_frame.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=3)
            entry = ttk.Entry(entry_frame, textvariable=var, width=12, font=('Segoe UI', 10))
            entry.pack(side="left", fill="x", expand=True)
            if shortcut == "HT":
                ttk.Button(
                    entry_frame,
                    text="Laser",
                    command=self.open_laser_dialog,
                    width=6,
                    state="disabled",  # Désactivation temporaire en attendant le correctif
                ).pack(side="left", padx=(5, 0))
            row_idx += 1
        ttk.Separator(input_frame, orient='horizontal').grid(row=row_idx, column=0, columnspan=4, sticky='ew', pady=10)
        row_idx += 1
        ttk.Label(input_frame, text="Nb Marches (Girons) :", font=('Segoe UI', 10, 'bold')).grid(row=row_idx, column=0, sticky="w", padx=5, pady=5)
        marches_control_frame = ttk.Frame(input_frame, style="InputControl.TFrame")
        marches_control_frame.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=5)
        marches_control_frame.columnconfigure(1, weight=1)
        ttk.Button(marches_control_frame, text="-", command=self.decrement_marches, width=3).grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(marches_control_frame, textvariable=self.nombre_marches_manuel_var, width=10, justify="center", font=('Segoe UI', 10)).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(marches_control_frame, text="+", command=self.increment_marches, width=3).grid(row=0, column=2, padx=(4, 0))
        ttk.Label(input_frame, text="Nb Contremarches (CM) :", font=('Segoe UI', 10, 'bold')).grid(row=row_idx, column=2, sticky="w", padx=5, pady=5)
        ttk.Label(
            input_frame,
            textvariable=self.nombre_cm_manuel_var,
            style="DisplayValue.TLabel",
            width=10,
            anchor="center",
            justify="center"
        ).grid(row=row_idx, column=3, sticky="ew", padx=5, pady=5)
        row_idx += 1
        ttk.Label(input_frame, text="Giron souhaité :", font=('Segoe UI', 10, 'bold')).grid(row=row_idx, column=0, sticky="w", padx=5, pady=5)
        giron_control_frame = ttk.Frame(input_frame, style="InputControl.TFrame")
        giron_control_frame.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=5)
        giron_control_frame.columnconfigure(1, weight=1)
        ttk.Button(giron_control_frame, text="-", command=self.decrement_giron, width=3).grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(giron_control_frame, textvariable=self.giron_souhaite_var, width=10, justify="center", font=('Segoe UI', 10)).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(giron_control_frame, text="+", command=self.increment_giron, width=3).grid(row=0, column=2, padx=(4, 0))
        ttk.Label(input_frame, text="Hauteur contremarche :", font=('Segoe UI', 10, 'bold')).grid(row=row_idx, column=2, sticky="w", padx=5, pady=5)
        ttk.Label(
            input_frame,
            textvariable=self.hauteur_cm_souhaitee_var,
            style="DisplayValue.TLabel",
            width=10,
            anchor="center",
            justify="center"
        ).grid(row=row_idx, column=3, sticky="ew", padx=5, pady=5)
        row_idx += 1
        ttk.Button(input_frame, text="Appliquer Valeurs Idéales (confort)", command=self.apply_ideal_values).grid(row=row_idx, column=0, columnspan=4, pady=10)

    def _create_results_frame(self, parent):
        results_frame = ttk.LabelFrame(parent, text="2. Résultats et Conformité")
        results_frame.pack(fill="x", pady=10)
        results_frame.columnconfigure(1, weight=1)
        results_frame.columnconfigure(2, weight=1)
        self.conformity_label = ttk.Label(results_frame, textvariable=self.conformity_status_var, style="Conformity.TLabel")
        self.conformity_label.grid(row=0, column=0, columnspan=3, pady=(5, 15), sticky="ew")
        results_labels_and_vars = [
            ("Hauteur réelle par CM :", self.hauteur_reelle_cm_res_var, self.hauteur_cm_message_var), ("Giron utilisé :", self.giron_utilise_res_var, self.giron_message_var),
            ("Longueur totale escalier :", self.longueur_totale_res_var, self.longueur_disponible_message_var), ("Angle de l'escalier :", self.angle_res_var, self.angle_message_var),
            ("Long. limon (approximative) :", self.limon_res_var, None), ("Échappée calculée (min.) :", self.echappee_res_var, self.echappee_message_var),
            ("Formule de Blondel (2H+G) :", self.blondel_message_var, None), ("Long. min. escalier (par giron) :", self.longueur_min_escalier_var, None),
            ("Écart Hauteur Totale :", self.hauteur_totale_ecart_message_var, None)
        ]
        for i, (text, res_var, msg_var) in enumerate(results_labels_and_vars, start=1):
            ttk.Label(results_frame, text=text).grid(row=i, column=0, sticky="w", padx=5, pady=5)
            if res_var in [self.blondel_message_var, self.longueur_min_escalier_var, self.hauteur_totale_ecart_message_var]:
                label = ttk.Label(results_frame, textvariable=res_var, font=('Segoe UI', 10, 'bold'))
                label.grid(row=i, column=1, sticky="w", padx=5, columnspan=2)
            else:
                ttk.Label(results_frame, textvariable=res_var, font=('Segoe UI', 10, 'bold')).grid(row=i, column=1, sticky="w", padx=5)
                if msg_var:
                    msg_label = ttk.Label(results_frame, textvariable=msg_var)
                    msg_label.grid(row=i, column=2, sticky="ew", padx=5)
                    msg_label.bind("<Configure>", lambda e, v=msg_var, w=msg_label: self._update_indicator_style(v, w))
                    self._update_indicator_style(msg_var, msg_label)

    def _update_indicator_style(self, var, widget):
        text = var.get()
        style_map = { "NON CONFORME": "Indicator.Red.TLabel", "TRÈS RAIDE": "Indicator.Red.TLabel", "LIMITE": "Indicator.Yellow.TLabel", "Confort Limité": "Indicator.Yellow.TLabel", "OK": "Indicator.Green.TLabel", "OPTIMAL": "Indicator.Green.TLabel", "Nul": "TLabel" }
        display_map = { "NON CONFORME": "❌ NON CONFORME", "TRÈS RAIDE": "❌ TRÈS RAIDE", "LIMITE": "⚠️ LIMITE", "Confort Limité": "⚠️ CONFORT LIMITÉ", "OK": "✅ OK", "OPTIMAL": "✅ OPTIMAL", "Nul": "✅ Nul" }
        style, display_text = "TLabel", text
        for key, s in style_map.items():
            if key in text: style = s; display_text = display_map.get(key, text); break
        widget.config(style=style, text=display_text)

    def _create_warnings_frame(self, parent):
        warnings_frame = ttk.LabelFrame(parent, text="4. Résumé des Avertissements")
        warnings_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.warnings_label = ttk.Label(warnings_frame, textvariable=self.warnings_var, wraplength=380, justify=tk.LEFT)
        self.warnings_label.pack(padx=10, pady=10, fill="both", expand=True)

    def _create_visual_tab(self, notebook):
        visual_frame = ttk.Frame(notebook, padding=5)
        self.canvas = tk.Canvas(visual_frame) 
        self.canvas.pack(expand=True, fill="both")
        notebook.add(visual_frame, text="Aperçu 2D")

    def _create_report_tab(self, notebook):
        report_frame = ttk.Frame(notebook, padding=5)
        self.report_text = tk.Text(report_frame, wrap="word", font=("Courier New", 9)) 
        self.report_text.pack(expand=True, fill="both")
        notebook.add(report_frame, text="Plan de Traçage")
    
    def _create_table_tab(self, notebook):
        table_frame = ttk.Frame(notebook, padding=5)
        self.table_text = tk.Text(table_frame, wrap="none", font=("Courier New", 9)) 
        self.table_text.pack(expand=True, fill="both")
        notebook.add(table_frame, text="Tableau des Marches")

    def _bind_events(self):
        for var_name, var_obj in self.tk_input_vars_dict.items():
            var_obj.trace_add("write", lambda *args, vn=var_name: self.recalculate_and_update_ui(changed_var_name=vn))
        self.nombre_cm_manuel_var.trace_add("write", lambda *args, vn="nombre_cm_manuel_var": self.recalculate_and_update_ui(changed_var_name=vn))
        self.nombre_marches_manuel_var.trace_add("write", lambda *args, vn="nombre_marches_manuel_var": self.recalculate_and_update_ui(changed_var_name=vn))
        self.canvas.bind("<Configure>", self.update_visual_preview)
        self.hauteur_totale_var.trace_add("write", lambda *args: self._update_from_height())

    def _update_from_height(self):
        """Met à jour les valeurs quand la hauteur totale change"""
        if self._controller:
            self._controller.handle_height_change()

    def _update_from_marches(self, new_nb_marches):
        """Met à jour les valeurs quand le nombre de marches change"""
        if self._controller:
            self._controller.handle_marches_change(new_nb_marches)

    def _update_from_cm(self, new_nb_cm):
        """Met à jour les valeurs quand le nombre de contremarches change"""
        if self._controller:
            self._controller.handle_cm_change(new_nb_cm)

    def decrement_cm(self):
        """Décrémente le nombre de contremarches"""
        if self._controller:
            self._controller.adjust_cm(-1)

    def increment_cm(self):
        """Incrémente le nombre de contremarches"""
        if self._controller:
            self._controller.adjust_cm(1)

    def decrement_marches(self):
        """Décrémente le nombre de marches"""
        if self._controller:
            self._controller.adjust_marches(-1)

    def increment_marches(self):
        """Incrémente le nombre de marches"""
        if self._controller:
            self._controller.adjust_marches(1)

    def decrement_hcm(self):
        if self._controller:
            self._controller.adjust_hcm(-0.125)

    def increment_hcm(self):
        if self._controller:
            self._controller.adjust_hcm(0.125)

    def decrement_giron(self):
        if self._controller:
            self._controller.adjust_giron(-0.125)

    def increment_giron(self):
        if self._controller:
            self._controller.adjust_giron(0.125)

    def apply_ideal_values(self):
        if self._controller and self._controller.apply_ideal_values():
            messagebox.showinfo("Valeurs Idéales", "Les valeurs de confort ont été appliquées.", parent=self)

    def recalculate_and_update_ui(self, *args, changed_var_name=None, force=False):
        if self._is_updating_ui and not force:
            return

        if force:
            if self._pending_recalc_id:
                try:
                    self.after_cancel(self._pending_recalc_id)
                except tk.TclError:
                    pass
            self._pending_recalc_id = None
            if changed_var_name is None:
                changed_var_name = self._last_changed_var
            self._perform_recalculate(changed_var_name=changed_var_name)
            return

        self._last_changed_var = changed_var_name or self._last_changed_var
        if self._pending_recalc_id:
            try:
                self.after_cancel(self._pending_recalc_id)
            except tk.TclError:
                pass

        delay = getattr(self, '_recalculate_delay_ms', 200)
        self._pending_recalc_id = self.after(
            delay,
            lambda: self._perform_recalculate(changed_var_name=self._last_changed_var)
        )

    def recalculate_and_update_ui(self, *args, changed_var_name=None):
        if self._is_updating_ui:
            return

        self._is_updating_ui = True
        self.clear_messages()

        try:
            if not self._controller:
                raise RuntimeError("Controller non initialisé.")

            calc_output = self._controller.perform_calculation(changed_var_name=changed_var_name)
            self.latest_results = calc_output["results"]
            self._update_interface_from_results(self.latest_results)
            self.update_results_display()
            self.update_warnings_display(calc_output["warnings"], calc_output["is_conform"])
            self.update_visual_preview()
            self.update_reports()

        except ValueError as ve:
            self.conformity_status_var.set("DONNÉES INVALIDES")
            self.warnings_var.set(f"Erreur de validation: {str(ve)}")
            if constants.DEBUG_MODE_ACTIVE:
                print(f"\nDEBUG - Erreur de validation: {str(ve)}")
        except Exception as e:
            self.conformity_status_var.set("ERREUR DE CALCUL")
            self.warnings_var.set(f"Une erreur inattendue s'est produite: {str(e)}")
            if constants.DEBUG_MODE_ACTIVE:
                import traceback
                print("\nDEBUG - Erreur inattendue:")
                traceback.print_exc()
        finally:
            self._is_updating_ui = False

    def _update_interface_from_results(self, results):
        """Nouvelle méthode pour centraliser la mise à jour des champs depuis les résultats"""
        if not results:
            return

        # Mise à jour des valeurs calculées
        if self.unites_var.get() == 'pouces':
            if results.get("hauteur_reelle_contremarche") is not None:
                self.hauteur_cm_souhaitee_var.set(
                    formatting.decimal_to_fraction_str(
                        results["hauteur_reelle_contremarche"], 
                        self.app_preferences
                    )
                )
            if results.get("giron_utilise") is not None:
                self.giron_souhaite_var.set(
                    formatting.decimal_to_fraction_str(
                        results["giron_utilise"], 
                        self.app_preferences
                    )
                )
        else:
            if results.get("hauteur_reelle_contremarche") is not None:
                self.hauteur_cm_souhaitee_var.set(
                    f"{results['hauteur_reelle_contremarche'] * constants.POUCE_EN_CM:.2f}"
                )
            if results.get("giron_utilise") is not None:
                self.giron_souhaite_var.set(
                    f"{results['giron_utilise'] * constants.POUCE_EN_CM:.2f}"
                )

        # Mise à jour des nombres de marches/contremarches
        if results.get("nombre_contremarches") is not None:
            self.nombre_cm_manuel_var.set(str(results["nombre_contremarches"]))
        if results.get("nombre_girons") is not None:
            self.nombre_marches_manuel_var.set(str(results["nombre_girons"]))

    def update_results_display(self):
        res, prefs = self.latest_results, self.app_preferences
        df = lambda v: formatting.decimal_to_fraction_str(v, prefs) if v is not None else ""
        if self.unites_var.get() == 'cm':
            df_mm = lambda v: f"{v * constants.POUCE_EN_CM:.2f} cm" if v is not None else ""
        else:
            df_mm = lambda v: f"{df(v)} ({round(v * constants.POUCE_EN_MM)} mm)" if v else ""
        if not res: self.clear_results_display(); return
        self.hauteur_reelle_cm_res_var.set(df_mm(res.get("hauteur_reelle_contremarche")))
        self.giron_utilise_res_var.set(df_mm(res.get('giron_utilise')))
        self.longueur_totale_res_var.set(df_mm(res.get("longueur_calculee_escalier")))
        self.angle_res_var.set(f"{res.get('angle_escalier', 0):.2f}°")
        self.limon_res_var.set(df_mm(res.get("longueur_limon_approximative")))
        self.echappee_res_var.set(df_mm(res.get("min_echappee_calculee")))
        nb_girons = res.get("nombre_girons", 0)
        self.longueur_min_escalier_var.set(f"Req: {df_mm(nb_girons * constants.GIRON_MIN_REGLEMENTAIRE)}" if nb_girons else "")
        self.hauteur_cm_message_var.set(res.get("hauteur_cm_message", ""))
        self.giron_message_var.set(res.get("giron_message", ""))
        self.echappee_message_var.set(res.get("echappee_message", ""))
        self.blondel_message_var.set(f"{res.get('blondel_message', '')} ({df(res.get('blondel_value'))}\")")
        self.longueur_disponible_message_var.set(res.get("longueur_disponible_message", ""))
        self.angle_message_var.set(res.get("angle_message", ""))
        self.hauteur_totale_ecart_message_var.set(res.get("hauteur_totale_ecart_message", ""))

    def update_warnings_display(self, warnings, is_conform):
        self.warnings_var.set("\n".join(warnings) if warnings else "Aucun avertissement.")
        if not is_conform:
            self.conformity_status_var.set("✗ NON CONFORME")
            self.conformity_label.config(foreground=self.themes[self.current_theme]["error"])
        elif warnings:
            self.conformity_status_var.set("CONFORME AVEC AVERTISSEMENTS")
            self.conformity_label.config(foreground=self.themes[self.current_theme]["warning"])
        else:
            self.conformity_status_var.set("✓ CONFORME")
            self.conformity_label.config(foreground=self.themes[self.current_theme]["success"])

    def clear_messages(self):
        for var in [self.warnings_var, self.hauteur_cm_message_var, self.giron_message_var, self.echappee_message_var, self.blondel_message_var, self.longueur_disponible_message_var, self.angle_message_var, self.hauteur_totale_ecart_message_var]: var.set("")
        self.conformity_status_var.set("EN ATTENTE")
        self.conformity_label.config(foreground=self.themes[self.current_theme]["fg"])

    def clear_results_display(self):
        for var in [self.hauteur_reelle_cm_res_var, self.giron_utilise_res_var, self.longueur_totale_res_var, self.angle_res_var, self.limon_res_var, self.echappee_res_var, self.longueur_min_escalier_var]: var.set("")
        self.clear_messages()

    def update_visual_preview(self, event=None):
        self.canvas.delete("all")
        canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
        nombre_girons = self.latest_results.get("nombre_girons")
        if nombre_girons is not None and nombre_girons > 0:
            res = self.latest_results
            giron, h_cm = res.get("giron_utilise", 0), res.get("hauteur_reelle_contremarche", 0)
            if giron <= 0 or h_cm <= 0: return
            total_w, total_h = res["nombre_girons"] * giron, res["nombre_contremarches"] * h_cm
            scale = min(canvas_width / total_w, canvas_height / total_h) * 0.8 if total_w > 0 and total_h > 0 else 1
            x, y = 50, canvas_height - 50
            for _ in range(res["nombre_girons"]):
                self.canvas.create_line(x, y, x + giron * scale, y, fill=self.themes[self.current_theme]["canvas_line"], width=2)
                x += giron * scale
                self.canvas.create_line(x, y, x, y - h_cm * scale, fill=self.themes[self.current_theme]["canvas_line"], width=2)
                y -= h_cm * scale
            self.canvas.create_text(canvas_width/2, 30, text=f"Escalier: {res['nombre_girons']} marches", fill=self.themes[self.current_theme]["canvas_line"], font=("Arial", 12, "bold"))

    def update_reports(self):
        if self.latest_results and self.latest_results.get("nombre_girons") is not None:
            plan = reporting.generer_texte_trace(self.latest_results, self.app_preferences)
            self.report_text.delete("1.0", tk.END); self.report_text.insert(tk.END, plan)
            params = reporting.generer_tableau_parametres(self.latest_results, self.app_preferences)
            marches = reporting.generer_tableau_marches(self.latest_results, self.app_preferences)
            self.table_text.delete("1.0", tk.END); self.table_text.insert(tk.END, f"{params}\n\n{marches}")
        else:
            msg = "Aucun résultat de calcul disponible."
            self.report_text.delete("1.0", tk.END); self.report_text.insert(tk.END, msg)
            self.table_text.delete("1.0", tk.END); self.table_text.insert(tk.END, msg)

    def open_preferences_dialog(self):
        PreferencesDialog(self, self.app_preferences)
        if file_operations and hasattr(file_operations, 'load_application_preferences'):
            self.app_preferences = file_operations.load_application_preferences()
        self.recalculate_and_update_ui()

    def open_laser_dialog(self):
        from core.laser_dialog import LaserDialog

        dlg = LaserDialog(self)
        self.wait_window(dlg)  # Attend la fermeture
        if getattr(dlg, "result", None):
            self.hauteur_totale_var.set(dlg.result)
    def export_pdf_report(self): messagebox.showinfo("Export PDF", "La fonction d'exportation PDF est en développement.", parent=self)




