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
