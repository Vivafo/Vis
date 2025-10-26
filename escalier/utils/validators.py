"""Utility helpers for validating and normalising user inputs.

Future refactors can move reusable validation logic from the UI layer
into this module so it can be unit-tested in isolation.
"""

from __future__ import annotations

from typing import Callable, Iterable, Mapping

ParserFn = Callable[[str], float]

__all__ = ["ensure_required", "prepare_main_inputs"]


def _normalise(value: str) -> str:
    return (value or "").strip().replace(",", ".")


def ensure_required(values: Mapping[str, str], required_keys: Iterable[str]) -> None:
    """Raise ValueError if one of the required keys contains an empty string."""
    missing = [key for key in required_keys if not values.get(key, "").strip()]
    if not missing:
        return
    if len(missing) == 1:
        raise ValueError(f"Le champ {missing[0]} est obligatoire")
    raise ValueError(f"Les champs suivants sont obligatoires: {', '.join(missing)}")


def prepare_main_inputs(
    raw_inputs: Mapping[str, str],
    *,
    parser_fn: ParserFn | None,
    required_numeric_keys: Iterable[str] | None = None,
) -> dict[str, str]:
    """
    Normalise and validate the main calculator inputs.

    Returns a trimmed copy of the inputs once mandatory numeric fields and
    minimum configuration rules have been validated.
    """

    values = {key: _normalise(value) for key, value in raw_inputs.items()}
    numeric_keys = tuple(required_numeric_keys or ("giron", "ep_plancher_sup", "ep_plancher_inf"))

    ensure_required(values, numeric_keys)
    _validate_numeric_formats(values, numeric_keys, parser_fn)
    _ensure_minimum_configuration(values)

    return values


def _validate_numeric_formats(
    values: Mapping[str, str],
    numeric_keys: Iterable[str],
    parser_fn: ParserFn | None,
) -> None:
    if parser_fn is None:
        raise ValueError("Module de formatage indisponible pour valider les champs numériques.")

    for key in numeric_keys:
        value = values.get(key, "")
        try:
            parser_fn(value)
        except Exception as exc:
            raise ValueError(f"Format invalide pour {key}: {value} ({exc})") from exc


def _ensure_minimum_configuration(values: Mapping[str, str]) -> None:
    combos = (
        bool(values.get("hauteur_totale")) and bool(values.get("hauteur_cm")),
        bool(values.get("nb_cm")) and bool(values.get("hauteur_cm")),
    )
    if not any(combos):
        raise ValueError(
            "Configuration invalide: fournir (hauteur totale ET hauteur CM) "
            "OU (nombre CM ET hauteur CM)"
        )
