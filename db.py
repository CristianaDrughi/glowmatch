"""Conexiune la baza de date SQLite si schema.

Foloseste sqlite3 din librarie standard - fara dependinte aditionale.
Context manager-ul get_db() asigura commit-ul si inchiderea conexiunii.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'app.db'


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    nume TEXT NOT NULL,
    brand TEXT NOT NULL,
    categorie TEXT NOT NULL,
    pret REAL NOT NULL CHECK(pret >= 0),
    tip_ten TEXT DEFAULT 'toate',
    subton TEXT DEFAULT 'toate',
    nuanta TEXT DEFAULT 'toate',
    finish TEXT DEFAULT 'natural',
    ocazie TEXT DEFAULT 'zi',
    acoperire TEXT DEFAULT 'toate',
    ingrediente_cheie TEXT DEFAULT '',
    vegan TEXT DEFAULT 'Nu',
    cruelty_free TEXT DEFAULT 'Nu',
    rating REAL DEFAULT 4.0 CHECK(rating >= 0 AND rating <= 5),
    descriere TEXT DEFAULT '',
    tip_produs TEXT DEFAULT 'makeup',
    contrast TEXT DEFAULT 'toate',
    baza TEXT DEFAULT 'toate',
    origine TEXT DEFAULT '',
    probleme TEXT DEFAULT '',
    fungal_acne_safe TEXT DEFAULT '',
    activ INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendations_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    preferinte_json TEXT NOT NULL,
    timp_executie_ms INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recommendation_products (
    log_id INTEGER NOT NULL REFERENCES recommendations_log(id) ON DELETE CASCADE,
    produs_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    pozitie INTEGER NOT NULL,
    scor INTEGER NOT NULL,
    PRIMARY KEY (log_id, produs_id)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol TEXT DEFAULT 'admin',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outbound_webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    log_id INTEGER REFERENCES recommendations_log(id) ON DELETE SET NULL,
    email TEXT DEFAULT '',
    url TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    response_body TEXT DEFAULT '',
    error TEXT DEFAULT '',
    durata_ms INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS extraction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    attribute_name TEXT NOT NULL,      -- ton / subton / culoare_ochi / culoare_par / ITA
    extracted_value TEXT NOT NULL,
    confidence_score REAL,             -- optional (ex. increderea pt subton)
    image_hash TEXT                    -- hash al pozei pt audit; NU stocam poza
);

CREATE TABLE IF NOT EXISTS test_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_filename TEXT NOT NULL,
    expected_skin_tone TEXT,
    expected_eye_color TEXT,
    expected_hair_color TEXT,
    expected_face_shape TEXT,          -- pastrat ca referinta experimentala
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_log_timestamp ON recommendations_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_recprod_produs ON recommendation_products(produs_id);
CREATE INDEX IF NOT EXISTS idx_webhook_timestamp ON outbound_webhooks(timestamp);
CREATE INDEX IF NOT EXISTS idx_webhook_status ON outbound_webhooks(status);
CREATE INDEX IF NOT EXISTS idx_extraction_timestamp ON extraction_log(timestamp);
"""


def logheaza_extractie(profil: dict, image_hash: str) -> None:
    """Salveaza in extraction_log fiecare atribut extras dintr-o analiza foto.
    NU stocheaza poza - doar un hash pentru audit."""
    increderi = {'subton': None}  # loc pentru scoruri de incredere viitoare
    atribute = ['ton', 'subton', 'culoare_ochi', 'culoare_par', 'ITA']
    with get_db() as conn:
        for atr in atribute:
            if atr in profil and profil[atr] is not None:
                conn.execute(
                    "INSERT INTO extraction_log (attribute_name, extracted_value, "
                    "confidence_score, image_hash) VALUES (?, ?, ?, ?)",
                    (atr, str(profil[atr]), increderi.get(atr), image_hash),
                )


# Coloane adaugate dupa versiunea initiala a schemei. Pentru bazele de date
# create inainte, le adaugam la pornire prin ALTER TABLE (SQLite nu modifica
# automat tabelele existente la CREATE TABLE IF NOT EXISTS).
COLOANE_NOI_PRODUCTS = {
    'tip_produs': "TEXT DEFAULT 'makeup'",
    'contrast': "TEXT DEFAULT 'toate'",
    'baza': "TEXT DEFAULT 'toate'",
    'origine': "TEXT DEFAULT ''",
    'probleme': "TEXT DEFAULT ''",
    'fungal_acne_safe': "TEXT DEFAULT ''",
    # Potrivire pe culoarea ochilor / parului extrasa din analiza foto.
    # Format ca restul: valori separate cu '|', sau 'toate' (universal).
    'suited_eye_color': "TEXT DEFAULT 'toate'",
    'suited_hair_color': "TEXT DEFAULT 'toate'",
    # Calea relativa catre poza produsului (in static/), ex: 'product_images/Clio - X.jpg'
    'image_path': "TEXT DEFAULT ''",
}


def _migreaza(conn):
    """Adauga coloanele noi pe o tabela products deja existenta (idempotent)."""
    existente = {r['name'] for r in conn.execute("PRAGMA table_info(products)")}
    for coloana, definitie in COLOANE_NOI_PRODUCTS.items():
        if coloana not in existente:
            conn.execute(f"ALTER TABLE products ADD COLUMN {coloana} {definitie}")


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)
        _migreaza(conn)
