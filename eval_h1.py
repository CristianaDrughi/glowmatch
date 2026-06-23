"""Comun pentru evaluarea H1 (precision@5): profiluri de test + cele 2 algoritme.

Folosit de:
  - genereaza_template_h1.py  (creeaza CSV-ul de etichetat manual, prin pooling)
  - eval_precision_at_5.py    (calculeaza precision@5 dupa ce ai etichetat)

Ambele importa de aici PROFILE + functiile de recomandare, ca rezultatele sa fie
IDENTICE intre generarea template-ului si evaluare (random e cu seed fix).
"""

import random

from recommender import recomanda

# 10 profiluri realiste (ton ten + culoare ochi + culoare par). Evitam combinatii
# rare nerealiste (ex. ten inchis + ochi albastri + par roscat).
PROFILE = [
    {'id': 1,  'nuanta': 'deschis', 'eye': 'blue',  'hair': 'blonde'},
    {'id': 2,  'nuanta': 'deschis', 'eye': 'green', 'hair': 'brunette'},
    {'id': 3,  'nuanta': 'deschis', 'eye': 'blue',  'hair': 'black'},
    {'id': 4,  'nuanta': 'mediu',   'eye': 'brown', 'hair': 'brunette'},
    {'id': 5,  'nuanta': 'mediu',   'eye': 'green', 'hair': 'black'},
    {'id': 6,  'nuanta': 'mediu',   'eye': 'brown', 'hair': 'black'},
    {'id': 7,  'nuanta': 'inchis',  'eye': 'brown', 'hair': 'black'},
    {'id': 8,  'nuanta': 'inchis',  'eye': 'brown', 'hair': 'brunette'},
    {'id': 9,  'nuanta': 'deschis', 'eye': 'brown', 'hair': 'blonde'},
    {'id': 10, 'nuanta': 'mediu',   'eye': 'blue',  'hair': 'blonde'},
]


def descriere(p):
    return f"ten {p['nuanta']} / ochi {p['eye']} / par {p['hair']}"


def preferinte(p):
    return {
        'tip_produs': 'makeup',
        'nuanta': p['nuanta'],
        'suited_eye_color': p['eye'],
        'suited_hair_color': p['hair'],
    }


def rule_based_top5(df, p):
    """Top 5 produse de la algoritmul rule-based ponderat."""
    rez, _ = recomanda(preferinte(p), df, numar=5, log=False)
    return list(rez['id'])


def random_top5(df, p):
    """Baseline: 5 produse aleatoare (unice), cu seed fix pe profil pt reproducere.
    Aplica aceleasi filtre dure ca rule-based (aici doar tip_produs=makeup)."""
    random.seed(42 + p['id'])
    pool = df[df['tip_produs'] == 'makeup']
    ids = list(pool['id'])
    return random.sample(ids, min(5, len(ids)))
