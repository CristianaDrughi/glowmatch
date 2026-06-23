"""Script temporar de calibrare: ruleaza analiza pe folderul de poze de test
si afiseaza ITA + Lab (L*, a*, b*) + ton/subton pentru fiecare poza.

Scop: gasirea unei reguli care separa tenul OLIVE (mediu) de cel DESCHIS
la valori ITA similare. Nu face parte din aplicatie - doar pentru calibrare.
"""

import os
import vision

FOLDER = r"C:\Users\Denisa\OneDrive\Desktop\LICENTA\Poza test ten"


def _numar(nume):
    # "poza test 4.jpg" -> 4, pentru sortare numerica corecta
    cifre = ''.join(c for c in nume if c.isdigit())
    return int(cifre) if cifre else 0


fisiere = sorted(
    [f for f in os.listdir(FOLDER) if f.lower().endswith(('.jpg', '.jpeg', '.png'))],
    key=_numar,
)

print(f"{'poza':<16}{'ITA':>8}{'L*':>8}{'a*':>8}{'b*':>8}  {'ton':<9}{'subton':<8}{'ratio a/b':>10}")
print("-" * 80)
for f in fisiere:
    r = vision.extract_profile(os.path.join(FOLDER, f))
    if not r.get('ok'):
        print(f"{f:<16}  EROARE: {r.get('error')}")
        continue
    L, a, b = r['Lab']
    ratio = (a / b) if b else 0
    print(f"{f:<16}{r['ITA']:>8}{L:>8}{a:>8}{b:>8}  {r['ton']:<9}{r['subton']:<8}{ratio:>10.2f}")
