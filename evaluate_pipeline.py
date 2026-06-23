"""evaluate_pipeline.py — evaluare sistematica a analizei foto (vision.py).

Ruleaza vision.py pe fiecare poza de test, compara rezultatul cu etichetele
REALE (notate manual, vizual) si raporteaza:
  - acuratetea pe TON (deschis / mediu / inchis) + matrice de confuzie
  - acuratetea pe SUBTON (cald / rece / neutru / olive)
  - acuratetea pe CULOAREA OCHILOR (blue / green / brown / hazel)

Schema de potrivire (documentata explicit pentru transparenta):
  - TON: potrivire EXACTA cu eticheta reala.
  - SUBTON si OCHI: eticheta reala vizuala e adesea COMPUSA (ex. "cald-neutru",
    "albastri-gri"). Consideram raspunsul corect daca algoritmul nimereste UNA
    dintre componentele acceptabile. Astfel evaluam corect cazurile de granita,
    fara sa penalizam o nuanta intermediara reala.

Pentru lucrare: cifrele de aici merg direct in tabelul de rezultate.
"""

import os
import vision

FOLDER = r"C:\Users\Denisa\OneDrive\Desktop\LICENTA\Poza test ten"

# Etichete REALE (adevarul de baza), notate vizual de operator pe pozele 3-22.
# ton: valoare unica.  subton/ochi: set de valori acceptabile.
ETICHETE = {
    3:  {"ton": "deschis", "subton": {"cald", "neutru"},   "ochi": {"green", "brown", "hazel"}, "par": "blonde"},
    4:  {"ton": "mediu",   "subton": {"neutru", "olive"},  "ochi": {"brown"},                   "par": "brunette"},
    5:  {"ton": "inchis",  "subton": {"cald"},             "ochi": {"brown"},                   "par": "black"},
    6:  {"ton": "inchis",  "subton": {"neutru"},           "ochi": {"brown"},                   "par": "black"},
    7:  {"ton": "mediu",   "subton": {"cald"},             "ochi": {"brown"},                   "par": "brunette"},
    8:  {"ton": "inchis",  "subton": {"neutru"},           "ochi": {"brown"},                   "par": "black"},
    9:  {"ton": "mediu",   "subton": {"cald"},             "ochi": {"brown"},                   "par": "black"},
    10: {"ton": "deschis", "subton": {"cald"},             "ochi": {"green", "brown", "hazel"}, "par": "red"},
    11: {"ton": "deschis", "subton": {"rece"},             "ochi": {"blue"},                    "par": "blonde"},
    12: {"ton": "deschis", "subton": {"neutru"},           "ochi": {"brown"},                   "par": "brunette"},
    13: {"ton": "deschis", "subton": {"cald", "neutru"},   "ochi": {"brown"},                   "par": "blonde"},
    14: {"ton": "deschis", "subton": {"neutru"},           "ochi": {"blue", "green"},           "par": "blonde"},
    15: {"ton": "deschis", "subton": {"rece", "neutru"},   "ochi": {"blue"},                    "par": "blonde"},
    16: {"ton": "deschis", "subton": {"rece"},             "ochi": {"blue"},                    "par": "blonde"},
    17: {"ton": "deschis", "subton": {"rece", "neutru"},   "ochi": {"green"},                   "par": "brunette"},
    18: {"ton": "deschis", "subton": {"neutru"},           "ochi": {"blue"},                    "par": "blonde"},
    19: {"ton": "deschis", "subton": {"neutru"},           "ochi": {"green"},                   "par": "brunette"},
    20: {"ton": "deschis", "subton": {"neutru", "rece"},   "ochi": {"blue"},                    "par": "black"},
    21: {"ton": "mediu",   "subton": {"cald", "olive"},    "ochi": {"brown"},                   "par": "black"},
    22: {"ton": "mediu",   "subton": {"neutru", "olive"},  "ochi": {"green"},                   "par": "brunette"},
}

TONURI = ["deschis", "mediu", "inchis"]


def _cale(numar):
    return os.path.join(FOLDER, f"poza test {numar}.jpg")


def main():
    ton_ok = subton_ok = ochi_ok = par_ok = 0
    ton_n = subton_n = ochi_n = par_n = 0
    # matrice de confuzie ton: confuzie[real][prezis]
    confuzie = {r: {p: 0 for p in TONURI} for r in TONURI}

    print(f"{'poza':<10}{'TON r/a':<20}{'SUBTON r/a':<24}{'OCHI r/a':<22}{'PAR r/a':<20}")
    print("-" * 110)

    for numar in sorted(ETICHETE):
        real = ETICHETE[numar]
        r = vision.extract_profile(_cale(numar))
        if not r.get("ok"):
            print(f"test {numar:<4}  EROARE: {r.get('error')}")
            continue

        # --- TON (potrivire exacta) ---
        ton_n += 1
        ton_corect = r["ton"] == real["ton"]
        ton_ok += ton_corect
        confuzie[real["ton"]][r["ton"]] += 1

        # --- SUBTON (in setul acceptabil) ---
        subton_n += 1
        subton_corect = r["subton"] in real["subton"]
        subton_ok += subton_corect

        # --- OCHI (in setul acceptabil) ---
        ochi_corect = None
        if r["culoare_ochi"] != "unknown":
            ochi_n += 1
            ochi_corect = r["culoare_ochi"] in real["ochi"]
            ochi_ok += ochi_corect

        # --- PAR (potrivire exacta; exclude 'unknown') ---
        par_corect = None
        if r["culoare_par"] != "unknown":
            par_n += 1
            par_corect = r["culoare_par"] == real["par"]
            par_ok += par_corect

        m_ton = "OK " if ton_corect else "GRESIT"
        m_sub = "OK " if subton_corect else "GRESIT"
        m_ochi = "n/a" if ochi_corect is None else ("OK " if ochi_corect else "GRESIT")
        m_par = "n/a" if par_corect is None else ("OK " if par_corect else "GRESIT")
        print(f"test {numar:<4}"
              f"{real['ton'] + '/' + r['ton']:<20}"
              f"{'/'.join(sorted(real['subton'])) + '/' + r['subton']:<24}"
              f"{'/'.join(sorted(real['ochi'])) + '/' + r['culoare_ochi']:<22}"
              f"{real['par'] + '/' + r['culoare_par']:<20}"
              f"  T:{m_ton} S:{m_sub} O:{m_ochi} P:{m_par}")

    def pct(ok, n):
        return f"{ok}/{n} = {100 * ok / n:.1f}%" if n else "n/a"

    print("\n" + "=" * 50)
    print("ACURATETE")
    print(f"  Ton    : {pct(ton_ok, ton_n)}")
    print(f"  Subton : {pct(subton_ok, subton_n)}")
    print(f"  Ochi   : {pct(ochi_ok, ochi_n)}  (exclus 'unknown')")
    print(f"  Par    : {pct(par_ok, par_n)}  (exclus 'unknown')")

    print("\nMATRICE DE CONFUZIE - TON (rand = real, coloana = prezis)")
    print(f"{'real\\prezis':<14}" + "".join(f"{t:<10}" for t in TONURI))
    for real_t in TONURI:
        rand = "".join(f"{confuzie[real_t][p]:<10}" for p in TONURI)
        print(f"{real_t:<14}{rand}")


if __name__ == "__main__":
    main()
