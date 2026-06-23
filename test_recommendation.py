"""Test pe profiluri sintetice pentru recommender-ul rule-based (Sprint 6).

Ruleaza `recomanda()` pe cateva profiluri scrise manual (ca cele produse de
analiza foto) si afiseaza top 5 produse + scor, ca sa verifici ca rezultatele
au sens. Masoara si timpul de executie (cerinta: < 1s pe catalog).

Profilurile folosesc atributele reale ale aplicatiei (nuanta/subton + culoarea
ochilor/parului din analiza foto, + filtre optionale categorie/buget).
"""

import time

from recommender import incarca_produse, recomanda

PROFILURI = [
    {
        'nume': 'Test 1: ten deschis + ochi albastri + par blond',
        'pref': {'tip_produs': 'makeup', 'nuanta': 'deschis', 'subton': 'rece',
                 'suited_eye_color': 'blue', 'suited_hair_color': 'blonde'},
    },
    {
        'nume': 'Test 2: ten inchis + ochi caprui + par negru',
        'pref': {'tip_produs': 'makeup', 'nuanta': 'inchis', 'subton': 'cald',
                 'suited_eye_color': 'brown', 'suited_hair_color': 'black'},
    },
    {
        'nume': 'Test 3: ten mediu (olive) + ochi verzi + par saten',
        'pref': {'tip_produs': 'makeup', 'nuanta': 'mediu', 'subton': 'olive',
                 'suited_eye_color': 'green', 'suited_hair_color': 'brunette'},
    },
    {
        'nume': 'Test 4: doar RUJ, buget max 80 RON, subton cald',
        'pref': {'tip_produs': 'makeup', 'categorie': 'Ruj', 'buget': '80',
                 'subton': 'cald', 'suited_hair_color': 'blonde'},
    },
    {
        'nume': 'Test 5: skincare, ten gras + acnee',
        'pref': {'tip_produs': 'skincare', 'tip_ten': 'gras',
                 'probleme': ['acnee cosmetica', 'pori inchisi']},
    },
]


def main():
    df = incarca_produse()
    print(f"Catalog: {len(df)} produse\n")

    for caz in PROFILURI:
        t0 = time.time()
        rezultate, _ = recomanda(caz['pref'], df, numar=5, log=False)
        dt = (time.time() - t0) * 1000

        print(f"=== {caz['nume']} ===   ({dt:.0f} ms)")
        if rezultate.empty:
            print("  (niciun produs - filtre prea stricte)")
        for _, p in rezultate.iterrows():
            print(f"  [{p['scor']:>2}] {p['categorie']:<22} {p['brand']} - {p['nume']}")
        print()


if __name__ == "__main__":
    main()
