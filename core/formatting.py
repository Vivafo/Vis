# core/formatting.py
from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

def parser_fraction(value: str) -> float:
    """
    Convertit une chaîne de type '7 1/4' ou '2.5' en float (pouces).
    """
    value = value.strip()
    if " " in value:  # ex: "7 1/4"
        whole, frac = value.split()
        return float(whole) + float(Fraction(frac))
    elif "/" in value:  # ex: "1/2"
        return float(Fraction(value))
    else:
        return float(value)

def decimal_to_fraction_str(value: float, preferences=None) -> str:
    """
    Convertit un float en fraction lisible (ex: 7.25 → '7 1/4').
    Limite volontairement les dénominateurs à 16 pour rester sur des fractions usuelles.
    """
    if value is None:
        return ""

    precision = 16
    frac = Fraction(round(value * precision), precision)
    is_negative = frac < 0
    frac = abs(frac)

    whole, remainder = divmod(frac.numerator, frac.denominator)
    if whole and remainder:
        result = f"{whole} {remainder}/{frac.denominator}"
    elif whole:
        result = str(whole)
    else:
        result = f"{remainder}/{frac.denominator}"

    return f"-{result}" if is_negative and result else result


def try_parse_float(value: Any) -> float | None:
    """
    Tente de convertir la valeur en float. Retourne None en cas d'échec.
    Les chaînes vides ou None sont interprétées comme 0.0 pour simplifier les agrégations.
    """
    if value in ("", None):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def aggregate_units_to_inches(
    *,
    pieds: Any = 0,
    pouces: Any = 0,
    fraction: Any = 0,
    metres: Any = 0,
    cm: Any = 0,
    mm: Any = 0,
) -> float | None:
    """
    Additionne plusieurs composantes de mesure pour produire une valeur en pouces.
    Retourne None si une composante ne peut pas être interprétée.
    """
    parts = []
    for value in (pieds, pouces, fraction, metres, cm, mm):
        parsed = try_parse_float(value)
        if parsed is None:
            return None
        parts.append(parsed)

    pieds_v, pouces_v, fraction_v, metres_v, cm_v, mm_v = parts
    return (
        (pieds_v * 12.0)
        + pouces_v
        + fraction_v
        + (metres_v * 39.3701)
        + (cm_v / 2.54)
        + (mm_v / 25.4)
    )


def inches_to_feet_inches_fraction(value: Any, *, denom: int = 16) -> str:
    """
    Formate une mesure en pouces sous la forme X' Y Z/W".
    Retourne '—' si la valeur n'est pas convertible.
    """
    try:
        total_inches = float(value)
    except (TypeError, ValueError):
        return "—"

    feet = int(total_inches // 12)
    remaining_inches = total_inches - (feet * 12)
    whole_inches = int(remaining_inches // 1)
    fractional_inches = remaining_inches - whole_inches

    numerator = round(fractional_inches * denom)
    if numerator == denom:
        whole_inches += 1
        numerator = 0

    if numerator:
        gcd = math.gcd(numerator, denom)
        numerator //= gcd
        denom //= gcd

    frac_part = f" {numerator}/{denom}" if numerator else ""
    return f"{feet}' {whole_inches}{frac_part}\""
