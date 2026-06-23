"""Genereaza CSV-ul de etichetat manual pentru H1 (precision@5), prin POOLING.

Pentru fiecare profil, aduna top 5 (rule-based) + top 5 (random) -> produse unice,
le amesteca (etichetare oarba) si scrie un rand per produs cu coloana 'is_relevant'
GOALA. Tu completezi Y (relevant pt profil) / N (nu).

Iesire: evaluation/ground_truth_recommendation.csv
"""

import csv
import random
from pathlib import Path

from eval_h1 import PROFILE, descriere, rule_based_top5, random_top5
from recommender import incarca_produse

OUT_DIR = Path(__file__).parent / 'evaluation'
OUT_CSV = OUT_DIR / 'ground_truth_recommendation.csv'

CAMPURI = ['profile_id', 'profil', 'product_id', 'brand', 'nume', 'categorie',
           'nuanta', 'subton', 'suited_eye_color', 'suited_hair_color', 'is_relevant']


def main():
    OUT_DIR.mkdir(exist_ok=True)
    df = incarca_produse()
    randuri = []

    for p in PROFILE:
        pool = list(dict.fromkeys(rule_based_top5(df, p) + random_top5(df, p)))  # unice
        random.seed(100 + p['id'])
        random.shuffle(pool)                                  # etichetare oarba
        for pid in pool:
            prod = df[df['id'] == pid].iloc[0]
            randuri.append({
                'profile_id': p['id'],
                'profil': descriere(p),
                'product_id': pid,
                'brand': prod['brand'],
                'nume': prod['nume'],
                'categorie': prod['categorie'],
                'nuanta': prod['nuanta'],
                'subton': prod['subton'],
                'suited_eye_color': prod['suited_eye_color'],
                'suited_hair_color': prod['suited_hair_color'],
                'is_relevant': '',                            # <-- completezi Y / N
            })

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=CAMPURI)
        w.writeheader()
        w.writerows(randuri)

    print(f"Scris {OUT_CSV} cu {len(randuri)} randuri de etichetat "
          f"({len(PROFILE)} profiluri).")


if __name__ == '__main__':
    main()
