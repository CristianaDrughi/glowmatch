"""Populeaza tabela test_cases cu ground truth-ul etichetat manual (vizual)
pentru pozele de test 3-22. Formalizeaza in DB ceea ce exista in
evaluate_pipeline.py + known_issues.md. Idempotent (sterge si re-insereaza).

Coloana expected_face_shape e pastrata ca REFERINTA experimentala (forma fetei
a fost scoasa din pipeline - rezultat negativ, vezi known_issues.md).
"""

from db import get_db

# numar: (ton, ochi (vizual), par, forma, observatie)
GROUND_TRUTH = {
    3:  ("deschis", "verzi-caprui",   "blonde",   "oval",   "lungime > latime, barbie usor ingustata"),
    4:  ("mediu",   "caprui",         "brunette", "oval",   "falca destul de definita (oval spre square)"),
    5:  ("inchis",  "caprui inchis",  "black",    "round",  "obraji plini, falca moale, lungime ~ latime"),
    6:  ("inchis",  "caprui inchis",  "black",    "oval",   "pometi lati, barbie mai ingusta (oval/heart)"),
    7:  ("mediu",   "caprui",         "brunette", "round",  "fata scurta, obraji plini"),
    8:  ("inchis",  "caprui inchis",  "black",    "oval",   "trasaturi moi (parul afro face evaluarea grea)"),
    9:  ("mediu",   "caprui inchis",  "black",    "square", "falca lata si unghiulara"),
    10: ("deschis", "verzi-caprui",   "red",      "oval",   "fata alungita, barbie ingusta"),
    11: ("deschis", "albastri deschis", "blonde", "round",  "obraji plini, falca moale"),
    12: ("deschis", "caprui",         "brunette", "oval",   "echilibrat, ingustare lina spre barbie"),
    13: ("deschis", "caprui deschis", "blonde",   "round",  "fata rotunjita (buclele mascheaza conturul)"),
    14: ("deschis", "albastri-verzi", "blonde",   "round",  "obraji plini"),
    15: ("deschis", "albastri-gri",   "blonde",   "oval",   "alungita (oval/heart)"),
    16: ("deschis", "albastri deschis", "blonde", "heart",  "pometi lati + barbie ascutita"),
    17: ("deschis", "verzi-gri",      "brunette", "square", "falca puternica, lungime ~ latime"),
    18: ("deschis", "albastri-gri",   "blonde",   "oval",   "fata ingusta, alungita"),
    19: ("deschis", "verzi",          "brunette", "oval",   "alungita, barbie ingustata (oval/heart)"),
    20: ("deschis", "albastri-gri",   "black",    "oval",   "falca definita (oval spre square)"),
    21: ("mediu",   "caprui inchis",  "black",    "oval",   "lungime > latime, barbie tapered"),
    22: ("mediu",   "verzi-gri",      "brunette", "oval",   "echilibrat (oval spre square)"),
}


def main():
    with get_db() as conn:
        conn.execute("DELETE FROM test_cases")   # idempotent
        for numar, (ton, ochi, par, forma, obs) in sorted(GROUND_TRUTH.items()):
            conn.execute(
                "INSERT INTO test_cases (image_filename, expected_skin_tone, "
                "expected_eye_color, expected_hair_color, expected_face_shape, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (f"poza test {numar}.jpg", ton, ochi, par, forma, obs),
            )
    print(f"Populat test_cases cu {len(GROUND_TRUTH)} cazuri de test (poze 3-22).")


if __name__ == "__main__":
    main()
