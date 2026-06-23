"""Motor de recomandare bazat pe reguli si scoring ponderat.

Logica:
  1. Filtre obligatorii (hard filters): categorie, buget, vegan, cruelty-free.
     Produsele care nu trec aceste filtre sunt eliminate complet.
  2. Scoring ponderat (soft scoring): fiecare criteriu care se potriveste
     aduce un numar de puncte. La final, produsele sunt sortate descrescator
     dupa scor, iar la egalitate se foloseste rating-ul ca tie-breaker.
  3. Ingredientele alese de utilizator contribuie incremental: fiecare
     ingredient prezent in produs adauga puncte (PONDERE_INGREDIENT).

Sursa de date: SQLite (tabela products). Fiecare apel la recomanda() este
logat in recommendations_log + recommendation_products pentru rapoarte.
"""

import json
import time

import pandas as pd

from db import get_db

# Ponderile sunt setate astfel incat criteriile critice pentru piele
# (tip ten, subton) sa cantareasca mai mult decat preferintele estetice.
PONDERI = {
    'tip_ten': 3,
    'subton': 2,
    'nuanta': 2,
    'acoperire': 2,
    'contrast': 1,
    'ocazie': 1,
    'finish': 1,
    # Pondere mica (tiebreaker): vin din analiza foto, cu acuratete moderata
    # (ochi ~63%, par ~72%), deci nu trebuie sa domine scorul.
    'suited_eye_color': 1,
    'suited_hair_color': 1,
}

ETICHETE = {
    'tip_ten': 'tipul tenului',
    'subton': 'subtonul',
    'nuanta': 'nuanta tenului',
    'acoperire': 'nivelul de acoperire',
    'contrast': 'contrastul',
    'ocazie': 'ocazia',
    'finish': 'finisajul preferat',
    'suited_eye_color': 'culoarea ochilor',
    'suited_hair_color': 'culoarea parului',
}

PONDERE_INGREDIENT = 2
PONDERE_PROBLEMA = 2

# Cuvinte prea generice pentru a conta la potrivirea problemelor pielii.
STOPWORDS_PROBLEME = {'de', 'la', 'si', 'a', 'pielii', 'piele'}


def incarca_produse() -> pd.DataFrame:
    with get_db() as conn:
        return pd.read_sql_query(
            "SELECT * FROM products WHERE activ = 1", conn
        )


def _se_potriveste(valoare_produs: str, valoare_user: str | None) -> bool:
    if not valoare_user or valoare_user == 'oricare':
        return True
    optiuni = str(valoare_produs).lower().split('|')
    if 'toate' in optiuni:
        return True
    return valoare_user.lower() in optiuni


def _ingrediente_potrivite(produs_ingrediente: str, preferinte_ingrediente: list[str]) -> list[str]:
    if not preferinte_ingrediente:
        return []
    set_produs = {x.strip().lower() for x in str(produs_ingrediente).split('|')}
    return [ing for ing in preferinte_ingrediente if ing.lower() in set_produs]


def _cuvinte(text: str) -> set[str]:
    """Cuvintele semnificative dintr-un text (pentru potrivirea problemelor)."""
    brute = str(text).lower().replace('|', ' ').replace(',', ' ').split()
    return {c.strip() for c in brute if c.strip() and c.strip() not in STOPWORDS_PROBLEME}


def _probleme_potrivite(produs_probleme: str, preferinte_probleme: list[str]) -> list[str]:
    """O problema aleasa de utilizator se potriveste daca imparte cel putin un
    cuvant-cheie cu problemele tinta ale produsului (vocabularul difera usor)."""
    if not preferinte_probleme:
        return []
    cuvinte_produs = _cuvinte(produs_probleme)
    potrivite = []
    for pb in preferinte_probleme:
        if _cuvinte(pb) & cuvinte_produs:
            potrivite.append(pb)
    return potrivite


def _scor(produs: pd.Series, preferinte: dict) -> tuple[int, list[str]]:
    scor = 0
    motive = []
    for camp, pondere in PONDERI.items():
        valoare_user = preferinte.get(camp)
        if valoare_user and valoare_user != 'oricare':
            if _se_potriveste(produs[camp], valoare_user):
                scor += pondere
                motive.append(ETICHETE[camp])

    ingr_match = _ingrediente_potrivite(
        produs.get('ingrediente_cheie'),
        preferinte.get('ingrediente_cheie', []),
    )
    if ingr_match:
        scor += PONDERE_INGREDIENT * len(ingr_match)
        motive.append('ingrediente: ' + ', '.join(ingr_match))

    pb_match = _probleme_potrivite(
        produs.get('probleme'),
        preferinte.get('probleme', []),
    )
    if pb_match:
        scor += PONDERE_PROBLEMA * len(pb_match)
        motive.append('probleme: ' + ', '.join(pb_match))

    return scor, motive


def recomanda(preferinte: dict, df: pd.DataFrame, numar: int = 5, log: bool = True) -> tuple[pd.DataFrame, int | None]:
    """Returneaza (rezultate_DataFrame, log_id) sau (rezultate, None) daca log=False."""
    inceput = time.time()
    rezultate = df.copy()

    # Hard filter pe tipul de produs (makeup vs skincare) - formularele sunt separate.
    tip_produs = preferinte.get('tip_produs')
    if tip_produs and 'tip_produs' in rezultate.columns:
        rezultate = rezultate[rezultate['tip_produs'] == tip_produs]

    categorie = preferinte.get('categorie')
    if categorie and categorie != 'oricare':
        rezultate = rezultate[rezultate['categorie'] == categorie]

    buget = preferinte.get('buget')
    if buget:
        try:
            rezultate = rezultate[rezultate['pret'] <= float(buget)]
        except (ValueError, TypeError):
            pass  # buget invalid (ex. text) -> ignoram filtrul, nu cracam

    if preferinte.get('doar_vegan'):
        rezultate = rezultate[rezultate['vegan'] == 'Da']

    if preferinte.get('doar_cruelty_free'):
        rezultate = rezultate[rezultate['cruelty_free'] == 'Da']

    scoruri_motive = [_scor(p, preferinte) for _, p in rezultate.iterrows()]
    rezultate = rezultate.assign(
        scor=[s for s, _ in scoruri_motive],
        motive=[m for _, m in scoruri_motive],
    )

    rezultate = rezultate.sort_values(
        by=['scor', 'rating'], ascending=[False, False]
    ).head(numar)

    log_id = None
    if log:
        elapsed_ms = int((time.time() - inceput) * 1000)
        log_id = _logheaza_recomandare(preferinte, rezultate, elapsed_ms)

    return rezultate, log_id


def _logheaza_recomandare(preferinte: dict, rezultate: pd.DataFrame, elapsed_ms: int) -> int:
    # Pastram doar preferintele care chiar conteaza (nu 'oricare' / gol / False)
    pref_curate = {
        k: v for k, v in preferinte.items()
        if v not in (None, '', 'oricare', False, [])
    }
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO recommendations_log (preferinte_json, timp_executie_ms) VALUES (?, ?)",
            (json.dumps(pref_curate, ensure_ascii=False), elapsed_ms),
        )
        log_id = cur.lastrowid
        for pozitie, (_, p) in enumerate(rezultate.iterrows(), start=1):
            conn.execute(
                "INSERT INTO recommendation_products (log_id, produs_id, pozitie, scor) "
                "VALUES (?, ?, ?, ?)",
                (log_id, int(p['id']), pozitie, int(p['scor'])),
            )
    return log_id
