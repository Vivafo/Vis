# calculateur.py
# Logiques de calcul séparées (IMPÉRIAL uniquement) :
# 1) Garde-corps (GC) — mode "equal_gaps" (jours égaux, extrémités incluses)
# 2) Marche / Giron — logique indépendante

import math

# ===== Utilitaires =====
def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return abs(a)

def inch_to_fraction_pow2_str(x: float, denom_max: int = 32) -> str:
    """
    Convertit une valeur en pouces vers une fraction impériale dont le dénominateur
    est une puissance de 2 jusqu'à denom_max (par défaut 1/32).
    Exemple: 4.3125 -> '4 5/16"'
    """
    if x is None:
        return "N/A"
    neg = x < 0
    x = abs(x)
    whole = int(math.floor(x))
    frac = x - whole

    # arrondir au plus proche 1/denom_max
    num = int(round(frac * denom_max))

    # Gérer le dépassement (ex: 3.999 -> 4 0/denom_max)
    if num == denom_max:
        whole += 1
        num = 0

    if num == 0:
        s = f'{whole}"'
    else:
        d = denom_max
        g = _gcd(num, d)
        num //= g
        d //= g
        s = f'{whole} {num}/{d}"' if whole > 0 else f'{num}/{d}"'

    return f'-{s}' if neg else s

def inch_decimal_str(x: float, places: int = 4) -> str:
    """Affiche la valeur en pouces décimaux (impérial), arrondie."""
    if x is None:
        return "N/A"
    fmt = "{:." + str(places) + "f}\""
    return fmt.format(x)

def round_to_1_over(denom: int, x: float) -> float:
    """Arrondit la valeur en pouces au plus proche 1/denom (ex: denom=32 -> 1/32)."""
    return round(x * denom) / denom

# ===== 1) GARDE-CORPS (GC) — equal_gaps =====
def gc_equal_gaps(L_in: float, W_in: float, O_max_in: float, denom_max:int=32):
    """
    Inputs (pouces) :
      L_in     : longueur nette entre poteaux
      W_in     : largeur d'un balustre
      O_max_in : ouverture claire maximale autorisée (ex. 4.00)
    Règles / Algorithme :
      N = ceil( (L_in - O_max_in) / (W_in + O_max_in) )
      g_in = (L_in - N * W_in) / (N + 1)
      s_in = W_in + g_in
      first_center_in = g_in + (W_in / 2)
      centers_in = [ first_center_in + i * s_in for i in range(0, N) ]
    Vérifications :
      0 < g_in <= O_max_in
      centers_in[0] - W_in/2 >= 0 ; centers_in[-1] + W_in/2 <= L_in
    """
    if min(L_in, W_in, O_max_in) <= 0:
        raise ValueError("L_in, W_in et O_max_in doivent être > 0 (pouces).")

    N = max(1, math.ceil((L_in - O_max_in) / (W_in + O_max_in)))
    g_in = (L_in - N * W_in) / (N + 1)
    s_in = W_in + g_in
    first_center_in = g_in + (W_in / 2.0)
    centers_in = [first_center_in + i * s_in for i in range(N)]

    ok_gaps = (g_in > 0) and (g_in <= O_max_in + 1e-12)
    ok_left = (centers_in[0] - W_in/2.0) >= -1e-9
    ok_right = (centers_in[-1] + W_in/2.0) <= (L_in + 1e-9)

    # affichage impérial (fraction facteur de 2 et décimal)
    display_frac = {
        "g_in": inch_to_fraction_pow2_str(g_in, denom_max),
        "s_in": inch_to_fraction_pow2_str(s_in, denom_max),
        "first_center_in": inch_to_fraction_pow2_str(first_center_in, denom_max),
        "centers_in": [inch_to_fraction_pow2_str(c, denom_max) for c in centers_in],
    }
    display_dec = {
        "g_in": inch_decimal_str(round_to_1_over(denom_max, g_in)),
        "s_in": inch_decimal_str(round_to_1_over(denom_max, s_in)),
        "first_center_in": inch_decimal_str(round_to_1_over(denom_max, first_center_in)),
        "centers_in": [inch_decimal_str(round_to_1_over(denom_max, c)) for c in centers_in],
    }

    return {
        "inputs": {"L_in": L_in, "W_in": W_in, "O_max_in": O_max_in},
        "mode": "equal_gaps",
        "outputs": {
            "N": N,
            "g_in": g_in,
            "s_in": s_in,
            "first_center_in": first_center_in,
            "centers_in": centers_in
        },
        "verification": {
            "g_in_leq_Omax": ok_gaps,
            "left_edge_ok": ok_left,
            "right_edge_ok": ok_right
        },
        "display_fraction_pow2": display_frac,
        "display_decimal_in": display_dec
    }

# ===== 2) MARCHE / GIRON (indépendant du GC) =====
def marche_centers(giron_in: float, balustre_largeur_in: float, espacement_maximum_in: float, denom_max:int=32):
    """
    Entrées (pouces) :
      giron_in : profondeur du giron
      balustre_largeur_in : largeur du balustre
      espacement_maximum_in : ouverture maximale permise (p.ex. 4.00)
    Règles (selon échanges corrigés) :
      N = ceil( giron_in / (espacement_maximum_in + balustre_largeur_in) )
      premier centre = balustre_largeur_in / 2
      pas (centre à centre) = giron_in / N
      centres[i] = premier_centre + i * pas
      ouverture claire = pas - balustre_largeur_in <= espacement_maximum_in
    """
    if min(giron_in, balustre_largeur_in, espacement_maximum_in) <= 0:
        raise ValueError("giron_in, balustre_largeur_in et espacement_maximum_in doivent être > 0 (pouces).")

    # Nombre minimal de balustres requis pour ne jamais dépasser l'ouverture admissible.
    N = max(1, math.ceil(giron_in / (espacement_maximum_in + balustre_largeur_in)))
    # Premier centre : on positionne le balustre initial à la moitié de sa largeur.
    first_center = balustre_largeur_in / 2.0
    # Pas centre-à-centre : giron réparti équitablement entre les N balustres.
    step = giron_in / N
    # Liste des positions centre à centre successives calculées à partir du premier centre et du pas.
    centers = [first_center + i * step for i in range(N)]

    # Vérifications (tolérance 1/32")
    tol = 1.0 / 32.0
    clear_spacing = step - balustre_largeur_in
    ok_clear = clear_spacing <= espacement_maximum_in + tol
    ok_left = first_center - (balustre_largeur_in / 2.0) >= -tol
    ok_right = centers[-1] + (balustre_largeur_in / 2.0) <= giron_in + tol

    verification = {
        "clear_spacing_leq_max": ok_clear,
        "left_edge_ok": ok_left,
        "right_edge_ok": ok_right,
        "end_within_1_32": ok_clear and ok_left and ok_right
    }

    display_frac = {
        "first_center_in": inch_to_fraction_pow2_str(first_center, denom_max),
        "step_in": inch_to_fraction_pow2_str(step, denom_max),
        "centers_in": [inch_to_fraction_pow2_str(c, denom_max) for c in centers],
    }
    display_dec = {
        "first_center_in": inch_decimal_str(round_to_1_over(denom_max, first_center)),
        "step_in": inch_decimal_str(round_to_1_over(denom_max, step)),
        "centers_in": [inch_decimal_str(round_to_1_over(denom_max, c)) for c in centers],
    }

    return {
        "inputs": {
            "giron_in": giron_in,
            "balustre_largeur_in": balustre_largeur_in,
            "espacement_maximum_in": espacement_maximum_in
        },
        "outputs": {
            "N": N,
            "first_center_in": first_center,
            "step_in": step,
            "centers_in": centers
        },
        "verification": verification,
        "display_fraction_pow2": display_frac,
        "display_decimal_in": display_dec
    }







