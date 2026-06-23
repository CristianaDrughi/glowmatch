"""Leaga pozele descarcate (de download_images.py) de produsele din DB.

Pasi:
  1. Citeste products.csv (are domeniu, categorie, brand, produs, nume_fisier).
  2. Pentru fiecare produs cu poza existenta pe disc (images/<domeniu>/<categorie>/),
     copiaza poza in static/product_images/ si seteaza products.image_path.
  3. Potrivire DB dupa (nume, brand) lowercase, ca la import_excel.py.

Ruleaza DUPA download_images.py:
    venv\\Scripts\\python.exe link_images.py
"""

import csv
import shutil
from pathlib import Path

from db import get_db, init_db

ROOT = Path(__file__).parent.parent          # ...\LICENTA
IMAGES_SRC = ROOT / 'images'
CSV_PATH = ROOT / 'products.csv'
STATIC_DEST = Path(__file__).parent / 'static' / 'product_images'


def main():
    init_db()                                # asigura coloana image_path
    STATIC_DEST.mkdir(parents=True, exist_ok=True)

    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    legate = fara_poza = nepotrivite = 0
    with get_db() as conn:
        for r in rows:
            src = IMAGES_SRC / r['domeniu'] / r['categorie'] / r['nume_fisier']
            if not src.exists():
                fara_poza += 1
                continue
            dest = STATIC_DEST / r['nume_fisier']
            if not dest.exists():
                shutil.copy(src, dest)
            rel = f"product_images/{r['nume_fisier']}"
            cur = conn.execute(
                "UPDATE products SET image_path = ? "
                "WHERE lower(trim(nume)) = ? AND lower(trim(brand)) = ?",
                (rel, r['produs'].strip().lower(), r['brand'].strip().lower()),
            )
            if cur.rowcount:
                legate += 1
            else:
                nepotrivite += 1

    print(f"Poze legate la produse: {legate}")
    print(f"Produse fara poza pe disc (inca nedescarcate): {fara_poza}")
    print(f"Poze fara produs corespondent in DB: {nepotrivite}")


if __name__ == "__main__":
    main()
