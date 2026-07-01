"""Interogari SQL agregate pentru rapoartele din admin.

Toate functiile intorc structuri simple (liste de dicturi) gata de serializat
in JSON pentru Chart.js.
"""

from db import get_db


ATRIBUTE_PROFIL = ['tip_ten', 'subton', 'nuanta', 'ocazie']


def top_produse(limit: int = 10) -> list[dict]:
    """R1 - Top N cele mai recomandate produse."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.nume, p.brand, p.categorie, COUNT(*) AS nr_recomandari
            FROM recommendation_products rp
            JOIN products p ON p.id = rp.produs_id
            GROUP BY p.id
            ORDER BY nr_recomandari DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def distributie_profiluri() -> dict:
    """R2 - Distributia valorilor pentru fiecare atribut din profilul utilizatorilor.

    Returneaza un dict cu cate o lista per atribut: { 'tip_ten': [{valoare, nr}, ...], ... }
    """
    rezultat = {}
    with get_db() as conn:
        for attr in ATRIBUTE_PROFIL:
            # Atributele vin dintr-o lista fixa - nu sunt input utilizator,
            # deci f-string-ul de mai jos e sigur fata de SQL injection.
            rows = conn.execute(f"""
                SELECT json_extract(preferinte_json, '$.{attr}') AS valoare,
                       COUNT(*) AS nr
                FROM recommendations_log
                WHERE json_extract(preferinte_json, '$.{attr}') IS NOT NULL
                GROUP BY valoare
                ORDER BY nr DESC
            """).fetchall()
            rezultat[attr] = [{'valoare': r['valoare'], 'nr': r['nr']} for r in rows]
    return rezultat


def evolutie_zilnica(zile: int = 30) -> list[dict]:
    """R3 - Numar recomandari per zi in ultimele N zile."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DATE(timestamp) AS zi, COUNT(*) AS nr
            FROM recommendations_log
            WHERE timestamp >= datetime('now', ?)
            GROUP BY zi
            ORDER BY zi
        """, (f'-{zile} days',)).fetchall()
    return [{'zi': r['zi'], 'nr': r['nr']} for r in rows]


def statistici_generale() -> dict:
    """Cifre rezumat pentru pagina de rapoarte."""
    with get_db() as conn:
        total_recomandari = conn.execute(
            "SELECT COUNT(*) AS n FROM recommendations_log"
        ).fetchone()['n']
        total_produse = conn.execute(
            "SELECT COUNT(*) AS n FROM products WHERE activ = 1"
        ).fetchone()['n']
        timp_mediu = conn.execute(
            "SELECT AVG(timp_executie_ms) AS m FROM recommendations_log"
        ).fetchone()['m'] or 0
    return {
        'total_recomandari': total_recomandari,
        'total_produse': total_produse,
        'timp_mediu_ms': round(timp_mediu, 1),
    }


# ---------- R4: Analiza foto AI ----------

ATRIBUTE_FOTO = ['ton', 'subton', 'culoare_ochi', 'culoare_par']


def analiza_foto_stats() -> dict:
    """R4 - Ce a detectat AI-ul din analizele foto reale (extraction_log)."""
    rezultat = {'distributie': {}}
    with get_db() as conn:
        rezultat['total_analize'] = conn.execute(
            "SELECT COUNT(DISTINCT image_hash) AS n FROM extraction_log"
        ).fetchone()['n']
        rezultat['ita_mediu'] = round(conn.execute(
            "SELECT AVG(CAST(extracted_value AS REAL)) AS m FROM extraction_log "
            "WHERE attribute_name = 'ITA'"
        ).fetchone()['m'] or 0, 1)
        for attr in ATRIBUTE_FOTO:
            rows = conn.execute(
                "SELECT extracted_value AS valoare, COUNT(*) AS nr FROM extraction_log "
                "WHERE attribute_name = ? GROUP BY valoare ORDER BY nr DESC", (attr,)
            ).fetchall()
            rezultat['distributie'][attr] = [
                {'valoare': r['valoare'], 'nr': r['nr']} for r in rows
            ]
    return rezultat


# ---------- Dashboard calitate catalog ----------

def calitate_catalog() -> dict:
    """Starea datelor din catalog: poze, rating, makeup/skincare, pe categorie."""
    with get_db() as conn:
        def scalar(q):
            return conn.execute(q).fetchone()[0]

        total = scalar("SELECT COUNT(*) FROM products")
        cu_poza = scalar("SELECT COUNT(*) FROM products WHERE image_path != ''")
        # rating = 4.0 e valoarea implicita data produselor fara nota reala
        rating_implicit = scalar("SELECT COUNT(*) FROM products WHERE rating = 4.0")
        makeup = scalar("SELECT COUNT(*) FROM products WHERE tip_produs = 'makeup'")
        skincare = scalar("SELECT COUNT(*) FROM products WHERE tip_produs = 'skincare'")
        pe_categorie = [
            {'categorie': r['categorie'], 'nr': r['nr']}
            for r in conn.execute(
                "SELECT categorie, COUNT(*) AS nr FROM products "
                "GROUP BY categorie ORDER BY nr DESC"
            )
        ]
    return {
        'total': total,
        'cu_poza': cu_poza, 'fara_poza': total - cu_poza,
        'rating_implicit': rating_implicit, 'rating_real': total - rating_implicit,
        'makeup': makeup, 'skincare': skincare,
        'pe_categorie': pe_categorie,
    }


# ---------- Cerere & dead-stock ----------

def cerere_categorii(limit: int = 10) -> list[dict]:
    """Cele mai cerute categorii (din preferintele utilizatorilor)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT json_extract(preferinte_json, '$.categorie') AS valoare, COUNT(*) AS nr
            FROM recommendations_log
            WHERE json_extract(preferinte_json, '$.categorie') IS NOT NULL
            GROUP BY valoare ORDER BY nr DESC LIMIT ?
        """, (limit,)).fetchall()
    return [{'valoare': r['valoare'], 'nr': r['nr']} for r in rows]


def cerere_probleme(limit: int = 10) -> list[dict]:
    """Cele mai cerute probleme ale pielii (campul e o lista in JSON)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT je.value AS valoare, COUNT(*) AS nr
            FROM recommendations_log rl,
                 json_each(COALESCE(json_extract(rl.preferinte_json, '$.probleme'), '[]')) je
            GROUP BY je.value ORDER BY nr DESC LIMIT ?
        """, (limit,)).fetchall()
    return [{'valoare': r['valoare'], 'nr': r['nr']} for r in rows]


def produse_nerecomandate() -> dict:
    """Produse care nu au aparut niciodata in vreo recomandare (dead stock)."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()['n']
        nerec = conn.execute("""
            SELECT COUNT(*) AS n FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM recommendation_products rp WHERE rp.produs_id = p.id
            )
        """).fetchone()['n']
        pe_tip = conn.execute("""
            SELECT tip_produs, COUNT(*) AS nr FROM products p
            WHERE NOT EXISTS (
                SELECT 1 FROM recommendation_products rp WHERE rp.produs_id = p.id
            )
            GROUP BY tip_produs
        """).fetchall()
    return {
        'total': total,
        'nerecomandate': nerec,
        'recomandate': total - nerec,
        'pe_tip': [{'tip': r['tip_produs'], 'nr': r['nr']} for r in pe_tip],
    }
