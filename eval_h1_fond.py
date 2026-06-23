"""H1 focalizat pe FOND DE TEN (unde alegerea nuantei conteaza cu adevarat).

Relevanta OBIECTIVA: un fond de ten e relevant pentru un profil daca nuanta lui
include tonul profilului (deschis/mediu/inchis). Compara precision@5:
  - rule-based (recomanda fonduri potrivite la ton)
  - random (5 fonduri aleatoare, seed fix)

Iesiri:
  evaluation/precision_at_5_fond.csv
  evaluation/visualizations/precision_at_5_fond.png
  actualizeaza evaluation/summary_h1.md
"""

import csv
import random
import statistics
from pathlib import Path

from eval_h1 import PROFILE, descriere
from recommender import incarca_produse, recomanda

EVAL = Path(__file__).parent / 'evaluation'
RESULTS = EVAL / 'precision_at_5_fond.csv'
VIZ = EVAL / 'visualizations'
PRAG = 0.4


def relevant(nuanta, ton):
    return ton in str(nuanta).split('|')


def rule_based_fond(df, p):
    pref = {'tip_produs': 'makeup', 'categorie': 'Fond de ten',
            'nuanta': p['nuanta'], 'suited_eye_color': p['eye'],
            'suited_hair_color': p['hair']}
    rez, _ = recomanda(pref, df, numar=5, log=False)
    return list(rez['id'])


def random_fond(df, p):
    random.seed(42 + p['id'])
    fonduri = list(df[df['categorie'] == 'Fond de ten']['id'])
    return random.sample(fonduri, min(5, len(fonduri)))


def precision(df, top5, ton):
    if not top5:
        return 0.0
    nuante = {int(r['id']): r['nuanta'] for _, r in df.iterrows()}
    rel = sum(1 for fid in top5 if relevant(nuante[fid], ton))
    return rel / len(top5)


def grafic(rb, rnd):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    VIZ.mkdir(parents=True, exist_ok=True)
    x = [p['id'] for p in PROFILE]
    fig, ax = plt.subplots(figsize=(10, 5))
    w = 0.4
    ax.bar([i - w/2 for i in x], rb, w, label='Rule-based', color='#b5547a')
    ax.bar([i + w/2 for i in x], rnd, w, label='Random', color='#bbbbbb')
    ax.set_xlabel('Profil'); ax.set_ylabel('Precision@5')
    ax.set_title('H1 (fond de ten): rule-based vs random')
    ax.set_xticks(x); ax.set_ylim(0, 1); ax.legend()
    fig.tight_layout(); fig.savefig(VIZ / 'precision_at_5_fond.png', dpi=120)
    print(f"Grafic: {VIZ / 'precision_at_5_fond.png'}")


def main():
    df = incarca_produse()
    rb_s, rnd_s = [], []
    EVAL.mkdir(exist_ok=True)
    with open(RESULTS, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['profile_id', 'profil', 'algorithm', 'returned', 'precision_at_5'])
        for p in PROFILE:
            for nume, top5 in (('rule_based', rule_based_fond(df, p)),
                               ('random', random_fond(df, p))):
                pr = precision(df, top5, p['nuanta'])
                w.writerow([p['id'], descriere(p), nume, top5, round(pr, 2)])
                (rb_s if nume == 'rule_based' else rnd_s).append(pr)

    rb_m, rnd_m = statistics.mean(rb_s), statistics.mean(rnd_s)
    dif = rb_m - rnd_m
    print(f"Rule-based : medie {rb_m:.2f} (std {statistics.pstdev(rb_s):.2f})")
    print(f"Random     : medie {rnd_m:.2f} (std {statistics.pstdev(rnd_s):.2f})")
    print(f"Diferenta  : {dif:.2f} (prag {PRAG}) -> H1 {'CONFIRMATA' if dif >= PRAG else 'PARTIAL'}")
    print("\nPer profil (rule-based / random):")
    for p, a, b in zip(PROFILE, rb_s, rnd_s):
        print(f"  P{p['id']} ({p['nuanta']:<7}): {a:.2f} / {b:.2f}")
    grafic(rb_s, rnd_s)


if __name__ == '__main__':
    main()
