"""Validare catalog (Sprint 5, Pas 4).

Verifica integritatea si echilibrul catalogului de produse:
  - campuri obligatorii completate (nume, brand, categorie, pret)
  - preturi pozitive, rating in [0, 5]
  - valori valide pentru suited_eye_color / suited_hair_color / vegan / cruelty_free
  - distributia per categorie si per ton (detecteaza bias-ul - relevant pt H2)

NOTA: catalogul NU contine URL-uri de imagini (produse text-only), deci
validarea de imagini din indicatii nu se aplica.
"""

from collections import Counter

from db import get_db

EYE_VALID = {"toate", "blue", "green", "brown", "hazel"}
HAIR_VALID = {"toate", "black", "brunette", "blonde", "red", "gray"}
BOOL_VALID = {"Da", "Nu"}
MIN_PE_CATEGORIE = 15   # prag minim sugerat pentru o categorie majora makeup


def _valori(camp):
    """Sparge un camp 'a|b' in set de valori."""
    return {p.strip() for p in str(camp).split('|') if p.strip()}


def main():
    with get_db() as conn:
        produse = conn.execute("SELECT * FROM products WHERE activ = 1").fetchall()

    probleme = []
    cat_counter = Counter()
    ten_counter = Counter()

    for p in produse:
        pid = p['id']
        # 1. Campuri obligatorii
        for camp in ('nume', 'brand', 'categorie'):
            if not p[camp] or not str(p[camp]).strip():
                probleme.append(f"[{pid}] camp obligatoriu gol: {camp}")
        # 2. Pret pozitiv
        if p['pret'] is None or p['pret'] <= 0:
            probleme.append(f"[{pid}] pret invalid: {p['pret']}")
        # 3. Rating in interval
        if p['rating'] is not None and not (0 <= p['rating'] <= 5):
            probleme.append(f"[{pid}] rating in afara [0,5]: {p['rating']}")
        # 4. suited_* valide
        if not _valori(p['suited_eye_color']) <= EYE_VALID:
            probleme.append(f"[{pid}] suited_eye_color invalid: {p['suited_eye_color']}")
        if not _valori(p['suited_hair_color']) <= HAIR_VALID:
            probleme.append(f"[{pid}] suited_hair_color invalid: {p['suited_hair_color']}")
        # 5. vegan / cruelty_free
        if p['vegan'] not in BOOL_VALID:
            probleme.append(f"[{pid}] vegan invalid: {p['vegan']}")
        if p['cruelty_free'] not in BOOL_VALID:
            probleme.append(f"[{pid}] cruelty_free invalid: {p['cruelty_free']}")

        if p['tip_produs'] == 'makeup':
            cat_counter[p['categorie']] += 1
            for t in _valori(p['tip_ten']):
                ten_counter[t] += 1

    # --- Raport ---
    print(f"Produse active: {len(produse)}")
    print(f"Probleme de integritate gasite: {len(probleme)}")
    for x in probleme[:30]:
        print("  ", x)
    if len(probleme) > 30:
        print(f"   ... si inca {len(probleme) - 30}")

    print("\nDistributie categorii MAKEUP (prag minim", MIN_PE_CATEGORIE, "):")
    for cat, n in cat_counter.most_common():
        semn = "OK" if n >= MIN_PE_CATEGORIE else "SUB PRAG"
        print(f"  {cat:<35} {n:>4}  {semn}")

    print("\nAcoperire pe tip ten (makeup):")
    for t, n in ten_counter.most_common():
        print(f"  {t:<12} {n}")

    print("\nImagini: N/A (catalogul nu contine URL-uri de imagini - produse text-only).")
    print("\nVERDICT:", "CATALOG VALID" if not probleme else f"{len(probleme)} probleme de rezolvat")


if __name__ == "__main__":
    main()
