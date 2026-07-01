"""Potriveste pozele din folderul "Poze produse" cu produsele din baza de date.

Fiecare fisier e denumit aproximativ "Brand Nume produs". Scriptul gaseste,
pentru fiecare poza, produsul cu cel mai asemanator "brand nume", copiaza poza
in static/images/produse/ si seteaza coloana `imagine` a produsului.

Utilizare:
  python import_poze.py --dry-run   # doar afiseaza potrivirile (nu scrie nimic)
  python import_poze.py             # copiaza pozele si actualizeaza baza de date
"""

import re
import shutil
import sys
from difflib import SequenceMatcher
from pathlib import Path

from db import get_db, init_db

POZE_DIR = Path(__file__).parent.parent / 'Poze produse'
DEST_DIR = Path(__file__).parent / 'static' / 'product_images'
EXT_OK = {'.jpg', '.jpeg', '.png', '.webp', '.jfif'}
PRAG_SIGUR = 0.72  # sub acest scor, potrivirea e considerata incerta


def normalizeaza(text: str) -> str:
    text = text.lower()
    text = re.sub(r'\.(jpg|jpeg|png|webp|jfif)$', '', text)
    text = re.sub(r'\(.*?\)', ' ', text)          # elimina "(seria)" etc.
    text = re.sub(r'[^a-z0-9]+', ' ', text)        # doar litere/cifre
    return re.sub(r'\s+', ' ', text).strip()


def scor(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def potriveste():
    poze = [p for p in POZE_DIR.iterdir() if p.suffix.lower() in EXT_OK]
    with get_db() as conn:
        produse = [
            {'id': r['id'], 'brand': r['brand'] or '', 'nume': r['nume']}
            for r in conn.execute("SELECT id, brand, nume FROM products")
        ]
    for p in produse:
        p['cheie'] = normalizeaza(f"{p['brand']} {p['nume']}")

    rezultate = []
    for poza in sorted(poze):
        cheie_poza = normalizeaza(poza.name)
        clasament = sorted(produse, key=lambda pr: scor(cheie_poza, pr['cheie']), reverse=True)
        best = clasament[0]
        s = scor(cheie_poza, best['cheie'])
        al2 = scor(cheie_poza, clasament[1]['cheie']) if len(clasament) > 1 else 0
        rezultate.append({'poza': poza, 'produs': best, 'scor': s, 'scor2': al2})
    return rezultate


def main(dry_run: bool):
    init_db()
    rezultate = potriveste()
    rezultate.sort(key=lambda r: r['scor'])

    incerte = [r for r in rezultate if r['scor'] < PRAG_SIGUR]
    sigure = [r for r in rezultate if r['scor'] >= PRAG_SIGUR]

    print(f"{len(rezultate)} poze | {len(sigure)} sigure (>= {PRAG_SIGUR}) | "
          f"{len(incerte)} incerte\n")

    if incerte:
        print("=== INCERTE (verifica manual) ===")
        for r in incerte:
            print(f"  [{r['scor']:.2f}] {r['poza'].name}")
            print(f"         -> #{r['produs']['id']} {r['produs']['brand']} {r['produs']['nume']}")
        print()

    print("=== SIGURE ===")
    for r in sigure:
        print(f"  [{r['scor']:.2f}] {r['poza'].name}  ->  "
              f"#{r['produs']['id']} {r['produs']['brand']} {r['produs']['nume']}")

    if dry_run:
        print("\nMod dry-run: nu am copiat poze si nu am modificat baza de date.")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)
    aplicate = 0
    with get_db() as conn:
        for r in rezultate:
            if r['scor'] < PRAG_SIGUR:
                continue
            ext = r['poza'].suffix.lower()
            nume_fisier = f"produs_{r['produs']['id']}{ext}"
            shutil.copy(r['poza'], DEST_DIR / nume_fisier)
            conn.execute("UPDATE products SET image_path=? WHERE id=?",
                         (f"product_images/{nume_fisier}", r['produs']['id']))
            aplicate += 1
    print(f"\nGata. Am asociat {aplicate} poze. Cele incerte au fost sarite.")


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
