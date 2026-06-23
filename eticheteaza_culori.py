"""Etichetare automata a campurilor suited_eye_color / suited_hair_color.

Nu avem nuanta exacta a fiecarui produs, deci folosim REGULI DE TEORIA CULORILOR
pe baza categoriei + subtonului produsului (pe care le avem). Aplicam potrivirea
DOAR unde conteaza estetic:
  - Fard de pleoape -> culoarea OCHILOR (nuante calde scot in evidenta ochii reci
    albastri/verzi; nuante reci -> verzi/caprui).
  - Ruj / Luciu de buze / Fard de obraz -> culoarea PARULUI (cald -> blond/roscat/
    saten; rece -> negru/saten).
Restul produselor raman 'toate' (universal - fond ten, mascara, pudra etc. nu
depind de ochi/par).

Euristica, documentata in known_issues.md. Ruleaza o singura data (idempotent).
"""

from db import get_db

CATEGORII_OCHI = {"Fard de pleoape"}
CATEGORII_PAR = {"Ruj", "Luciu de buze", "Fard de obraz"}


def _temperatura(subton: str) -> str:
    """'cald' / 'rece' / 'mixt' din subtonul produsului (poate fi 'cald|rece' etc.)."""
    parti = {p.strip().lower() for p in str(subton).split('|')}
    cald = 'cald' in parti
    rece = 'rece' in parti
    if cald and not rece:
        return 'cald'
    if rece and not cald:
        return 'rece'
    return 'mixt'


def _eticheta_ochi(temp: str) -> str:
    if temp == 'cald':  return "blue|green"      # nuante calde -> ochi reci ies in evidenta
    if temp == 'rece':  return "green|brown"     # nuante reci -> verzi/caprui
    return "toate"


def _eticheta_par(temp: str) -> str:
    if temp == 'cald':  return "blonde|red|brunette"
    if temp == 'rece':  return "black|brunette"
    return "toate"


def main():
    with get_db() as conn:
        produse = conn.execute(
            "SELECT id, categorie, subton FROM products WHERE tip_produs = 'makeup'"
        ).fetchall()

        n_ochi = n_par = 0
        for p in produse:
            temp = _temperatura(p['subton'])
            if p['categorie'] in CATEGORII_OCHI:
                conn.execute(
                    "UPDATE products SET suited_eye_color = ? WHERE id = ?",
                    (_eticheta_ochi(temp), p['id']),
                )
                n_ochi += 1
            elif p['categorie'] in CATEGORII_PAR:
                conn.execute(
                    "UPDATE products SET suited_hair_color = ? WHERE id = ?",
                    (_eticheta_par(temp), p['id']),
                )
                n_par += 1

    print(f"Etichetate: {n_ochi} produse pe culoarea ochilor, {n_par} pe culoarea parului.")
    print("Restul raman 'toate' (universal).")


if __name__ == "__main__":
    main()
