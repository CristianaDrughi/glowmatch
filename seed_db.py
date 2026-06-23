"""Initializeaza baza de date: schema + catalog complet + test_cases + admin.

Reconstruieste `data/app.db` din fisierele CSV comise in repo (catalogul NU se
tine in git ca baza de date binara - evita scurgeri de date personale).

Utilizare:
  python seed_db.py                  # genereaza o parola admin aleatoare
  python seed_db.py parola_mea       # foloseste parola data ca argument

Ruleaza-l o data dupa clonarea repo-ului. Reincarca produsele si test_cases
(DELETE + INSERT) si creeaza/actualizeaza utilizatorul admin.
"""

import secrets
import sys
from pathlib import Path

import pandas as pd
from werkzeug.security import generate_password_hash

from db import DB_PATH, get_db, init_db

DATA_DIR = Path(__file__).parent / 'data'
PRODUCTS_CSV = DATA_DIR / 'products.csv'
TEST_CASES_CSV = DATA_DIR / 'test_cases.csv'

# Coloane numerice din products.csv (restul sunt text).
NUMERIC_INT = {'id', 'activ'}
NUMERIC_FLOAT = {'pret', 'rating'}


def seed_products():
    df = pd.read_csv(PRODUCTS_CSV, keep_default_na=False)
    cols = list(df.columns)
    collist = ', '.join(cols)
    placeholders = ', '.join(['?'] * len(cols))
    with get_db() as conn:
        conn.execute("DELETE FROM products")
        for _, row in df.iterrows():
            vals = []
            for col in cols:
                v = row[col]
                if col in NUMERIC_INT:
                    v = int(v) if str(v).strip() else 0
                elif col in NUMERIC_FLOAT:
                    v = float(v) if str(v).strip() else 0.0
                else:
                    v = str(v)
                vals.append(v)
            conn.execute(
                f"INSERT INTO products ({collist}) VALUES ({placeholders})", vals
            )
    print(f"Importate {len(df)} produse in {DB_PATH}.")


def seed_test_cases():
    if not TEST_CASES_CSV.exists():
        return
    df = pd.read_csv(TEST_CASES_CSV, keep_default_na=False)
    with get_db() as conn:
        conn.execute("DELETE FROM test_cases")
        for _, row in df.iterrows():
            conn.execute(
                "INSERT INTO test_cases (image_filename, expected_skin_tone, "
                "expected_eye_color, expected_hair_color, expected_face_shape, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (row['image_filename'], row['expected_skin_tone'],
                 row['expected_eye_color'], row['expected_hair_color'],
                 row['expected_face_shape'], row['notes']),
            )
    print(f"Importate {len(df)} cazuri de test.")


def seed_admin(username: str = 'admin', password: str | None = None):
    if password is None:
        password = secrets.token_urlsafe(12)
        print("\n" + "=" * 60)
        print(f"  Parola admin generata: {password}")
        print(f"  Username: {username}")
        print("  Salveaza-o intr-un loc sigur - nu o vei mai vedea.")
        print("=" * 60 + "\n")
    pw_hash = generate_password_hash(password)
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE admin_users SET password_hash = ? WHERE username = ?",
                (pw_hash, username),
            )
            print(f"Utilizator admin '{username}' actualizat cu parola noua.")
        else:
            conn.execute(
                "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
                (username, pw_hash),
            )
            print(f"Utilizator admin '{username}' creat.")


if __name__ == '__main__':
    init_db()
    seed_products()
    seed_test_cases()
    parola = sys.argv[1] if len(sys.argv) > 1 else None
    seed_admin(password=parola)
    print("\nGata. Poti porni aplicatia cu: python app.py")
