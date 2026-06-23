"""Importa produsele din fisierul Excel (makeup + skincare) in baza de date.

Fisierul Excel are doua foi de produse ('Makeup' si 'Skincare'), fiecare cu
categoriile scrise ca randuri-titlu ("Fond de ten (30 produse)") intre produse.
Coloanele si vocabularul difera de schema bazei de date, asa ca scriptul:
  1. parcurge fiecare foaie rand cu rand, retinand categoria curenta;
  2. normalizeaza valorile (coduri tip ten G/M/U/N/S -> cuvinte, separatori / , - -> |);
  3. adauga produsele in tabela `products` (fara a sterge cele existente).

Utilizare:
  python import_excel.py              # import real (necesita coloanele Pret si Rating)
  python import_excel.py --dry-run    # doar previzualizare, fara scriere in DB

Pretul si rating-ul nu exista in fisierul original. Adauga in fiecare foaie de
produse cate o coloana cu antetul 'Pret' si una cu antetul 'Rating', apoi ruleaza
scriptul. Daca lipsesc, scriptul ruleaza automat in modul --dry-run.
"""

import re
import sys
from pathlib import Path

import pandas as pd

from db import get_db, init_db

XLSX_PATH = Path(__file__).parent.parent / 'Produse_Makeup_Skincare_Kbeauty_Europa_2.0.xlsx'

# Codurile folosite in coloana "Tip ten potrivit"
COD_TIP_TEN = {
    'g': 'gras', 'u': 'uscat', 'm': 'mixt', 'n': 'normal', 's': 'sensibil',
    'toate': 'toate',
}

# Separatori posibili intre valori multiple: / , ; liniute, sageti, "sau"
_SEP = re.compile(r'[\/,;–—\-→]|\bsau\b', re.IGNORECASE)


def _este_gol(val) -> bool:
    return pd.isna(val) or str(val).strip() in ('', '-', 'nan')


def normalize_lista(val, coduri: dict | None = None) -> str:
    """Imparte un text in valori, le normalizeaza si le uneste cu '|'."""
    if _este_gol(val):
        return ''
    text = re.sub(r'\(.*?\)', '', str(val))  # elimina paranteze: "(40 nuante)" etc.
    tokenuri = [t.strip().lower() for t in _SEP.split(text) if t.strip()]
    rezultat = []
    for t in tokenuri:
        if coduri is not None:
            if t in coduri:
                t = coduri[t]
            else:
                continue  # token necunoscut (ex: "dupa varianta") - ignorat
        if t and t not in rezultat:
            rezultat.append(t)
    return '|'.join(rezultat)


def normalize_da_nu(val) -> str:
    if _este_gol(val):
        return 'Nu'
    return 'Da' if str(val).strip().lower().startswith('da') else 'Nu'


def parse_pret(val) -> float | None:
    """Pretul e dat ca interval ('45-65 RON') -> luam mijlocul intervalului."""
    if _este_gol(val):
        return None
    numere = [float(n) for n in re.findall(r'\d+(?:[.,]\d+)?', str(val).replace(',', '.'))]
    if not numere:
        return None
    return round(sum(numere) / len(numere), 1)


def parse_rating(val) -> float | None:
    """Rating-ul e fie gol ('—'), fie text cu numarul inglobat ('4.7/5 (...)')."""
    if _este_gol(val):
        return None
    m = re.search(r'\d(?:\.\d+)?', str(val))
    if not m:
        return None
    nota = float(m.group())
    return nota if 0 <= nota <= 5 else None


def curata_categorie(text: str) -> str:
    # Elimina doar sufixul "(NN produse)", pastrand eventuale paranteze descriptive
    # din nume (ex: "Cleanser (apos) / Gel de curatare").
    return re.sub(r'\s*\(\s*\d+\s*produse\s*\).*$', '', str(text), flags=re.IGNORECASE).strip()


# Maparea field_db -> lista de antete posibile (potrivire dupa subsir, lowercase)
CONFIG = {
    'makeup': {
        'nume': ['produs'],
        'brand': ['brand'],
        'origine': ['origine'],
        'tip_ten': ['tip ten'],
        'subton': ['subton'],
        'contrast': ['contrast'],
        'nuanta': ['nuanta'],
        'finish': ['finisaj'],
        'descriere': ['note'],
        'pret': ['pret', 'pret (ron)', 'pret ron'],
        'rating': ['rating'],
    },
    'skincare': {
        'nume': ['produs'],
        'brand': ['brand'],
        'origine': ['origine'],
        'tip_ten': ['tip ten'],
        'probleme': ['probleme'],
        'ingrediente_cheie': ['ingrediente'],
        'fungal_acne_safe': ['fungal'],
        'descriere': ['note'],
        'pret': ['pret', 'pret (ron)', 'pret ron'],
        'rating': ['rating'],
    },
}


def _gaseste_coloane(header_row, config: dict) -> dict:
    """Construieste field_db -> index coloana pe baza randului de antet."""
    antete = {j: str(v).strip().lower() for j, v in enumerate(header_row) if not pd.isna(v)}
    mapare = {}
    for field, variante in config.items():
        for j, text in antete.items():
            if any(v in text for v in variante):
                mapare[field] = j
                break
    return mapare


def parse_sheet(path: Path, sheet: str) -> tuple[list[dict], bool]:
    """Returneaza (produse, are_pret_rating)."""
    config = CONFIG[sheet.lower()]
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    produse = []
    categorie = None
    coloane = {}  # sticky: pastram coloanele gasite (antetul se repeta per categorie)
    for _, row in raw.iterrows():
        c0 = '' if pd.isna(row[0]) else str(row[0]).strip()
        if 'produse)' in c0.lower():
            categorie = curata_categorie(c0)
            continue
        if c0.lower() == 'nr':
            coloane.update(_gaseste_coloane(row, config))
            continue
        # rand de produs: prima celula e un numar
        if not c0.replace('.0', '').isdigit() or not coloane:
            continue

        def cell(field):
            j = coloane.get(field)
            return row[j] if j is not None else None

        nume = cell('nume')
        if _este_gol(nume):
            continue

        p = {
            'tip_produs': sheet.lower(),
            'categorie': categorie or '',
            'nume': str(nume).strip(),
            'brand': '' if _este_gol(cell('brand')) else str(cell('brand')).strip(),
            'origine': '' if _este_gol(cell('origine')) else str(cell('origine')).strip(),
            'tip_ten': normalize_lista(cell('tip_ten'), COD_TIP_TEN) or 'toate',
            'descriere': '' if _este_gol(cell('descriere')) else str(cell('descriere')).strip(),
        }

        if sheet.lower() == 'makeup':
            p['subton'] = normalize_lista(cell('subton')) or 'toate'
            p['contrast'] = normalize_lista(cell('contrast')) or 'toate'
            p['nuanta'] = normalize_lista(cell('nuanta')) or 'toate'
            p['finish'] = normalize_lista(cell('finish')) or 'natural'
        else:
            p['probleme'] = normalize_lista(cell('probleme'))
            p['ingrediente_cheie'] = normalize_lista(cell('ingrediente_cheie'))
            p['fungal_acne_safe'] = normalize_da_nu(cell('fungal_acne_safe'))

        # Pret (interval -> mijloc) / rating (text -> numar, implicit 4.0)
        p['pret'] = parse_pret(cell('pret'))
        p['rating'] = parse_rating(cell('rating'))
        produse.append(p)

    are_pret_rating = 'pret' in (coloane or {}) and 'rating' in (coloane or {})
    return produse, are_pret_rating


def importa(dry_run: bool = False):
    init_db()
    toate = []
    are_pret_rating = True
    for sheet in ['Makeup', 'Skincare']:
        produse, ok = parse_sheet(XLSX_PATH, sheet)
        are_pret_rating = are_pret_rating and ok
        print(f"  {sheet}: {len(produse)} produse parsate"
              f"{'' if ok else '  (lipsesc coloanele Pret/Rating)'}")
        toate.extend(produse)

    if not are_pret_rating:
        print("\nNu am gasit coloanele 'Pret' si 'Rating' in fisier.")
        print("Trec automat in modul --dry-run (nu scriu in baza de date).")
        dry_run = True

    # Evita duplicatele: nu reimporta un produs (nume+brand) deja existent
    with get_db() as conn:
        existente = {
            (r['nume'].strip().lower(), (r['brand'] or '').strip().lower())
            for r in conn.execute("SELECT nume, brand FROM products")
        }
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) m FROM products").fetchone()['m']

    de_adaugat = []
    sarite = 0
    for p in toate:
        cheie = (p['nume'].strip().lower(), p['brand'].strip().lower())
        if cheie in existente:
            sarite += 1
            continue
        existente.add(cheie)
        de_adaugat.append(p)

    print(f"\nDe adaugat: {len(de_adaugat)} | deja existente (sarite): {sarite}")

    if dry_run:
        print("\n--- PREVIZUALIZARE (primele 3 produse normalizate) ---")
        for p in de_adaugat[:3]:
            for k, v in p.items():
                print(f"   {k}: {v}")
            print()
        print("Mod dry-run: nu am scris nimic in baza de date.")
        return

    next_id = max_id + 1
    with get_db() as conn:
        for p in de_adaugat:
            conn.execute("""
                INSERT INTO products (id, nume, brand, categorie, pret, tip_ten, subton,
                    nuanta, finish, ocazie, acoperire, ingrediente_cheie, vegan, cruelty_free,
                    rating, descriere, tip_produs, contrast, baza, origine, probleme,
                    fungal_acne_safe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                next_id, p['nume'], p['brand'], p['categorie'],
                p.get('pret') or 0.0,
                p['tip_ten'], p.get('subton', 'toate'), p.get('nuanta', 'toate'),
                p.get('finish', 'natural'), 'zi', 'toate',
                p.get('ingrediente_cheie', ''), 'Nu', 'Nu',
                p.get('rating') or 4.0, p['descriere'], p['tip_produs'],
                p.get('contrast', 'toate'), 'toate', p['origine'],
                p.get('probleme', ''), p.get('fungal_acne_safe', ''),
            ))
            next_id += 1
    print(f"\nGata. Am adaugat {len(de_adaugat)} produse noi in baza de date.")


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    print(f"Import din: {XLSX_PATH}\n")
    importa(dry_run=dry)
