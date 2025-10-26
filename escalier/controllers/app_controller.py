"""Application controller coordinating the UI and business logic."""

from __future__ import annotations

from typing import Any, Callable, Optional

try:
    from core import constants
except ImportError as exc:  # pragma: no cover - config issue during startup
    raise ImportError("Impossible d'importer core.constants") from exc

try:
    from core import formatting
except ImportError:
    formatting = None  # type: ignore[assignment]

try:
    from core import calculations
except ImportError as exc:  # pragma: no cover - config issue during startup
    raise ImportError("Impossible d'importer core.calculations") from exc

from escalier.utils.validators import prepare_main_inputs


ParserFn = Optional[Callable[[str], float]]
FormatterFn = Optional[Callable[[float, dict], str]]


class AppController:
    """Coordinate interactions between the Tkinter view and the core logic."""

    def __init__(self, view: Any) -> None:
        self.view = view
        self._parser_fn: ParserFn = getattr(formatting, "parser_fraction", None) if formatting else None
        self._format_fn: FormatterFn = getattr(formatting, "decimal_to_fraction_str", None) if formatting else None
        self._connect_view()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _connect_view(self) -> None:
        if hasattr(self.view, "set_controller"):
            self.view.set_controller(self)

    def initialize(self) -> None:
        """Run an initial refresh so the UI reflects the current preferences."""
        try:
            self.view.recalculate_and_update_ui()
        except Exception as exc:  # pragma: no cover - defensive logging for UI path
            print(f"Erreur lors de l'initialisation de l'interface: {exc}")

    def request_recalculate(self, changed_var: Optional[str] = None) -> None:
        """Public entry point to trigger a new calculation from other modules."""
        self.view.recalculate_and_update_ui(changed_var_name=changed_var)

    def perform_calculation(self, *, changed_var_name: Optional[str] = None):
        """Execute the main calculation and return a structured payload for the view."""

        raw_inputs = {
            "hauteur_totale": self.view.hauteur_totale_var.get(),
            "hauteur_cm": self.view.hauteur_cm_souhaitee_var.get(),
            "nb_cm": self.view.nombre_cm_manuel_var.get(),
            "nb_marches": self.view.nombre_marches_manuel_var.get(),
            "giron": self.view.giron_souhaite_var.get(),
            "ep_plancher_sup": self.view.epaisseur_plancher_sup_var.get(),
            "ep_plancher_inf": self.view.epaisseur_plancher_inf_var.get(),
        }

        parser_fn = getattr(formatting, "parser_fraction", None) if formatting else None
        input_values = prepare_main_inputs(raw_inputs, parser_fn=parser_fn)

        if getattr(constants, "DEBUG_MODE_ACTIVE", False):
            print("\nDEBUG - Valeurs d'entrée normalisées:")
            for key, value in input_values.items():
                print(f"  {key}: '{value}'")

        unite_calcul = "Pouces" if self.view.unites_var.get() == "pouces" else "Centimètres"
        if getattr(constants, "DEBUG_MODE_ACTIVE", False):
            print(f"\nDEBUG - Lancement calcul avec unité: {unite_calcul}")

        calc_output = calculations.calculer_escalier_ajuste(
            hauteur_totale_escalier_str=input_values["hauteur_totale"],
            giron_souhaite_str=input_values["giron"],
            hauteur_cm_souhaitee_str=input_values["hauteur_cm"],
            nombre_marches_manuel_str=input_values["nb_marches"],
            nombre_cm_manuel_str=input_values["nb_cm"],
            epaisseur_plancher_sup_str=input_values["ep_plancher_sup"],
            epaisseur_plancher_inf_str=input_values["ep_plancher_inf"],
            profondeur_tremie_ouverture_str=self.view.profondeur_tremie_ouverture_var.get(),
            position_tremie_ouverture_str=self.view.position_tremie_var.get(),
            espace_disponible_str=self.view.espace_disponible_var.get(),
            loaded_app_preferences_dict=self.view.app_preferences,
            changed_var_name=changed_var_name,
            unite=unite_calcul,
        )

        results = calc_output.get("results", {})
        if getattr(constants, "DEBUG_MODE_ACTIVE", False):
            print("\nDEBUG - Résultats reçus:", bool(results))
            if results:
                print("  - nb_girons:", results.get("nombre_girons"))
                print("  - hauteur_cm:", results.get("hauteur_reelle_contremarche"))
                print("  - giron:", results.get("giron_utilise"))

        if not results:
            raise ValueError("Aucun résultat retourné par le calcul")

        return {
            "results": results,
            "warnings": calc_output.get("warnings", []),
            "is_conform": calc_output.get("is_conform", False),
            "unit": unite_calcul,
            "inputs": input_values,
        }

    # ------------------------------------------------------------------
    # Event handlers wired from the view
    # ------------------------------------------------------------------
    def handle_height_change(self) -> None:
        if getattr(self.view, "_is_updating_ui", False):
            return

        height = self._parse_user_number(self.view.hauteur_totale_var.get())
        if height is None or height <= 0:
            return

        hcm_ideal = constants.HAUTEUR_CM_CONFORT_CIBLE
        nb_cm = max(2, round(height / hcm_ideal))
        hcm_reel = height / nb_cm

        try:
            self.view._is_updating_ui = True
            self.view.nombre_cm_manuel_var.set(str(nb_cm))
            self.view.nombre_marches_manuel_var.set(str(nb_cm - 1))
            self._set_fraction(self.view.hauteur_cm_souhaitee_var, hcm_reel)
        finally:
            self.view._is_updating_ui = False

        self.request_recalculate("hauteur_totale_var")

    def handle_marches_change(self, new_nb_marches: int) -> None:
        if getattr(self.view, "_is_updating_ui", False):
            return
        if new_nb_marches < 1 or new_nb_marches > 49:
            return

        nb_cm = new_nb_marches + 1
        height = self._parse_user_number(self.view.hauteur_totale_var.get())

        try:
            self.view._is_updating_ui = True
            self.view.nombre_marches_manuel_var.set(str(new_nb_marches))
            self.view.nombre_cm_manuel_var.set(str(nb_cm))
            if height and height > 0:
                hcm = height / nb_cm
                self._set_fraction(self.view.hauteur_cm_souhaitee_var, hcm)
        finally:
            self.view._is_updating_ui = False

        self.request_recalculate("nombre_marches_manuel_var")

    def handle_cm_change(self, new_nb_cm: int) -> None:
        if getattr(self.view, "_is_updating_ui", False):
            return
        if new_nb_cm < 2 or new_nb_cm > 50:
            return

        height = self._parse_user_number(self.view.hauteur_totale_var.get())

        try:
            self.view._is_updating_ui = True
            self.view.nombre_cm_manuel_var.set(str(new_nb_cm))
            self.view.nombre_marches_manuel_var.set(str(new_nb_cm - 1))
            if height and height > 0:
                hcm = height / new_nb_cm
                self._set_fraction(self.view.hauteur_cm_souhaitee_var, hcm)
        finally:
            self.view._is_updating_ui = False

        self.request_recalculate("nombre_cm_manuel_var")

    # ------------------------------------------------------------------
    # Increment / decrement helpers
    # ------------------------------------------------------------------
    def adjust_cm(self, delta: int) -> None:
        current = self._safe_int(self.view.nombre_cm_manuel_var.get())
        if current is None:
            return
        new_value = current + delta
        self.handle_cm_change(new_value)

    def adjust_marches(self, delta: int) -> None:
        current = self._safe_int(self.view.nombre_marches_manuel_var.get())
        if current is None:
            return
        new_value = current + delta
        self.handle_marches_change(new_value)

    def adjust_hcm(self, delta: float) -> None:
        current = self._parse_fraction(self.view.hauteur_cm_souhaitee_var.get())
        if current is None:
            return
        new_value = current + delta
        new_value = max(constants.HAUTEUR_CM_MIN_REGLEMENTAIRE, min(constants.HAUTEUR_CM_MAX_REGLEMENTAIRE, new_value))
        self._set_fraction(self.view.hauteur_cm_souhaitee_var, new_value)
        self.request_recalculate("hauteur_cm_souhaitee_var")

    def adjust_giron(self, delta: float) -> None:
        current = self._parse_fraction(self.view.giron_souhaite_var.get())
        if current is None:
            return
        new_value = current + delta
        new_value = max(constants.GIRON_MIN_REGLEMENTAIRE, min(constants.GIRON_MAX_REGLEMENTAIRE, new_value))
        self._set_fraction(self.view.giron_souhaite_var, new_value)
        self.request_recalculate("giron_souhaite_var")

    # ------------------------------------------------------------------
    # High level actions
    # ------------------------------------------------------------------
    def apply_ideal_values(self) -> bool:
        default_tread = (self.view.app_preferences.get("default_tread_width_straight", "9 1/4") or "").replace('"', "")
        giron_decimal = self._parse_fraction(default_tread)
        if giron_decimal is None:
            if getattr(constants, "DEBUG_MODE_ACTIVE", False):
                print(f"DEBUG - impossible de parser la valeur de giron par défaut: '{default_tread}'")
            return False

        hcm_target = constants.HAUTEUR_CM_CONFORT_CIBLE
        try:
            self.view._is_updating_ui = True
            self._set_fraction(self.view.giron_souhaite_var, giron_decimal)
            self._set_fraction(self.view.hauteur_cm_souhaitee_var, hcm_target)

            total_height = self._parse_fraction(self.view.hauteur_totale_var.get())
            if total_height and total_height > 0:
                nb_cm = max(2, round(total_height / hcm_target))
                self.view.nombre_cm_manuel_var.set(str(nb_cm))
                self.view.nombre_marches_manuel_var.set(str(nb_cm - 1))
        finally:
            self.view._is_updating_ui = False

        self.request_recalculate("apply_ideal_values")
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_user_number(self, raw_value: Optional[str]) -> Optional[float]:
        value = (raw_value or "").strip()
        if not value:
            return None
        normalized = value.replace(",", ".")
        try:
            if self._parser_fn:
                return self._parser_fn(normalized)
            return float(normalized)
        except Exception:
            if getattr(constants, "DEBUG_MODE_ACTIVE", False):
                print(f"DEBUG - valeur numérique invalide: '{raw_value}'")
            return None

    def _parse_fraction(self, raw_value: Optional[str]) -> Optional[float]:
        if not raw_value:
            return None
        parser = self._parser_fn
        if not parser:
            return self._parse_user_number(raw_value)
        try:
            return parser(raw_value.replace(",", "."))
        except Exception:
            if getattr(constants, "DEBUG_MODE_ACTIVE", False):
                print(f"DEBUG - fraction invalide: '{raw_value}'")
            return None

    def _set_fraction(self, tk_var: Any, value: float) -> None:
        formatted = self._format_fraction(value)
        tk_var.set(formatted)

    def _format_fraction(self, value: float) -> str:
        format_fn = self._format_fn
        if format_fn:
            try:
                return format_fn(value, self.view.app_preferences)
            except Exception:
                pass
        return f"{value:.3f}"

    @staticmethod
    def _safe_int(raw_value: Optional[str]) -> Optional[int]:
        try:
            return int((raw_value or "0").strip() or "0")
        except ValueError:
            return None
