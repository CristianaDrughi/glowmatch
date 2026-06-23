"""Calculeaza precision@5 pentru rule-based vs random baseline (H1).

Citeste etichetele manuale din evaluation/ground_truth_recommendation.csv,
re-ruleaza ambele algoritme (deterministe, random cu seed fix) si calculeaza,
pentru fiecare profil: precision@5 = produse relevante in top 5 / 5.

Iesiri:
  evaluation/precision_at_5_results.csv   (per profil x algoritm)
  evaluation/summary_h1.md                (sinteza + verdict H1)
  evaluation/visualizations/precision_at_5.png  (grafic)
"""

import csv
import statistics
from pathlib import Path

from eval_h1 import PROFILE, descriere, rule_based_top5, random_top5
from recommender import incarca_produse

EVAL = Path(__file__).parent / 'evaluation'
GT = EVAL / 'ground_truth_recommendation.csv'
RESULTS = EVAL / 'precision_at_5_results.csv'
SUMMARY = EVAL / 'summary_h1.md'
VIZ = EVAL / 'visualizations'

PRAG_H1 = 0.4   # diferenta minima rule-based - random pt a confirma H1


def incarca_etichete():
    rel, goale = {}, 0
    with open(GT, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            v = (r['is_relevant'] or '').strip().upper()
            if not v:
                goale += 1
            rel[(int(r['profile_id']), int(r['product_id']))] = v.startswith('Y')
    return rel, goale


def precision_at_5(top5, profile_id, rel):
    if not top5:
        return 0.0
    relevante = sum(1 for pid in top5 if rel.get((profile_id, pid), False))
    return relevante / len(top5)


def grafic(rb_scores, rnd_scores):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib indisponibil - sar peste grafic)")
        return
    VIZ.mkdir(parents=True, exist_ok=True)
    x = [p['id'] for p in PROFILE]
    fig, ax = plt.subplots(figsize=(10, 5))
    w = 0.4
    ax.bar([i - w/2 for i in x], rb_scores, w, label='Rule-based', color='#b5547a')
    ax.bar([i + w/2 for i in x], rnd_scores, w, label='Random', color='#bbbbbb')
    ax.set_xlabel('Profil'); ax.set_ylabel('Precision@5')
    ax.set_title('Precision@5: rule-based vs random baseline')
    ax.set_xticks(x); ax.set_ylim(0, 1); ax.legend()
    fig.tight_layout()
    fig.savefig(VIZ / 'precision_at_5.png', dpi=120)
    print(f"Grafic salvat: {VIZ / 'precision_at_5.png'}")


def main():
    rel, goale = incarca_etichete()
    if goale:
        print(f"ATENTIE: {goale} randuri NEetichetate (is_relevant gol) -> tratate ca N.")
        print("Completeaza-le pentru rezultate corecte.\n")

    df = incarca_produse()
    rb_scores, rnd_scores = [], []
    with open(RESULTS, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['profile_id', 'profil', 'algorithm', 'returned_products',
                    'relevant_count', 'precision_at_5'])
        for p in PROFILE:
            for nume, top5 in (('rule_based', rule_based_top5(df, p)),
                               ('random', random_top5(df, p))):
                pr = precision_at_5(top5, p['id'], rel)
                rel_n = round(pr * len(top5))
                w.writerow([p['id'], descriere(p), nume, top5, rel_n, round(pr, 2)])
                (rb_scores if nume == 'rule_based' else rnd_scores).append(pr)

    rb_m, rnd_m = statistics.mean(rb_scores), statistics.mean(rnd_scores)
    rb_sd = statistics.pstdev(rb_scores)
    rnd_sd = statistics.pstdev(rnd_scores)
    dif = rb_m - rnd_m
    confirmat = dif >= PRAG_H1

    print(f"Rule-based : medie {rb_m:.2f} (std {rb_sd:.2f}) | >=0.6: "
          f"{sum(1 for s in rb_scores if s >= 0.6)}/10")
    print(f"Random     : medie {rnd_m:.2f} (std {rnd_sd:.2f}) | >=0.6: "
          f"{sum(1 for s in rnd_scores if s >= 0.6)}/10")
    print(f"Diferenta  : {dif:.2f} (prag {PRAG_H1}) -> "
          f"H1 {'CONFIRMATA' if confirmat else 'NECONFIRMATA'}")

    SUMMARY.write_text(f"""# H1 - Rule-based vs Random baseline (precision@5)

Evaluare pe {len(PROFILE)} profiluri, etichetare manuala (pooling top-5).

| Algoritm | Precision@5 medie | Std | Cazuri >= 0.6 |
|----------|-------------------|-----|----------------|
| Rule-based ponderat | {rb_m:.2f} | {rb_sd:.2f} | {sum(1 for s in rb_scores if s >= 0.6)}/10 |
| Random baseline | {rnd_m:.2f} | {rnd_sd:.2f} | {sum(1 for s in rnd_scores if s >= 0.6)}/10 |

- Diferenta: {dif:.2f} (prag {PRAG_H1})
- **H1 {'CONFIRMATA' if confirmat else 'NECONFIRMATA'}**

## H2 - Acuratete analiza ten (set 20 poze)
- Ton (depth, 3 cat.): 100%
- Subton (4 cat.): 40% (limitare documentata - lumina)
- **H2 confirmata** (depth solid; subton slab, ca bias documentat)

## H3 - Forma fetei (raporturi geometrice)
- Rapoarte simple: ~35% < baseline majoritar 60% (predictie constanta 'oval')
- **H3 confirmata** (metoda geometrica simpla insuficienta -> rezultat negativ)
""", encoding='utf-8')
    print(f"\nSinteza scrisa: {SUMMARY}")
    grafic(rb_scores, rnd_scores)


if __name__ == '__main__':
    main()
