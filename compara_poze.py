"""Compara produsele din DB cu cele din Excel-ul cu poze
(Produse_..._+poze.xlsx) si raporteaza produsele din DB care NU se gasesc in
Excel (deci pentru care nu exista poza inca).

Potrivire dupa cheia (nume, brand) - lowercase + strip, ca la import_excel.py.
"""

from pathlib import Path

import pandas as pd

from db import get_db

XLSX_POZE = Path(__file__).parent.parent / 'Produse_Makeup_Skincare_Kbeauty_Europa+poze(756).xlsx'


def _cheie(nume, brand):
    n = '' if pd.isna(nume) else str(nume).strip().lower()
    b = '' if pd.isna(brand) else str(brand).strip().lower()
    return (n, b)


def parse_poze(sheet):
    """Returneaza set de chei (nume, brand) prezente in Excel-ul cu poze."""
    raw = pd.read_excel(XLSX_POZE, sheet_name=sheet, header=None)
    col_brand = col_nume = None
    chei = set()
    for _, row in raw.iterrows():
        c0 = '' if pd.isna(row[0]) else str(row[0]).strip()
        if c0.lower() == 'nr':                       # rand de antet
            for j, v in enumerate(row):
                if pd.isna(v):
                    continue
                t = str(v).strip().lower()
                if 'brand' in t:
                    col_brand = j
                elif 'produs' in t:
                    col_nume = j
            continue
        if not c0.replace('.0', '').isdigit() or col_nume is None:
            continue
        nume = row[col_nume]
        brand = row[col_brand] if col_brand is not None else None
        if pd.isna(nume) or not str(nume).strip():
            continue
        chei.add(_cheie(nume, brand))
    return chei


def main():
    chei_poze = parse_poze('Makeup') | parse_poze('Skincare')
    print(f"Produse in Excel-ul cu poze: {len(chei_poze)}")

    with get_db() as conn:
        produse = conn.execute(
            "SELECT nume, brand, categorie, tip_produs FROM products WHERE activ = 1"
        ).fetchall()

    lipsa = [p for p in produse if _cheie(p['nume'], p['brand']) not in chei_poze]
    print(f"Produse in DB: {len(produse)}")
    print(f"Produse din DB FARA poza (nu sunt in Excel): {len(lipsa)}\n")

    # Grupate pe tip_produs + categorie
    lipsa.sort(key=lambda p: (p['tip_produs'], p['categorie'], p['brand']))
    cat_curenta = None
    for p in lipsa:
        eticheta = f"{p['tip_produs']} / {p['categorie']}"
        if eticheta != cat_curenta:
            cat_curenta = eticheta
            print(f"\n--- {eticheta} ---")
        print(f"  {p['brand']} - {p['nume']}")


if __name__ == "__main__":
    main()
