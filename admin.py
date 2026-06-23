"""Blueprint admin: CRUD produse + API JSON pentru rapoarte.

Toate rutele necesita autentificare (@login_required) - Flask-Login
redirectioneaza utilizatorii nelogati la /admin/login.
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

import reports
from db import get_db

admin_bp = Blueprint('admin', __name__)

# Optiunile valide pentru dropdown-urile din formularul de produs.
OPTIUNI = {
    'tip_ten': ['toate', 'uscat', 'gras', 'mixt', 'normal', 'sensibil'],
    'subton': ['toate', 'cald', 'rece', 'neutru'],
    'nuanta': ['toate', 'deschis', 'mediu', 'inchis'],
    'finish': ['mat', 'satinat', 'luminos', 'natural'],
    'ocazie': ['zi', 'seara', 'eveniment'],
    'acoperire': ['toate', 'lejera', 'medie', 'totala'],
    'vegan': ['Da', 'Nu'],
    'cruelty_free': ['Da', 'Nu'],
}


@admin_bp.route('/')
@login_required
def home():
    return redirect(url_for('admin.products'))


# ---------- CRUD produse ----------

@admin_bp.route('/products')
@login_required
def products():
    cautare = request.args.get('q', '').strip()
    with get_db() as conn:
        if cautare:
            rows = conn.execute("""
                SELECT * FROM products
                WHERE nume LIKE ? OR brand LIKE ? OR categorie LIKE ?
                ORDER BY categorie, nume
            """, (f'%{cautare}%', f'%{cautare}%', f'%{cautare}%')).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM products ORDER BY categorie, nume"
            ).fetchall()
    return render_template('admin/products.html', produse=rows, cautare=cautare)


@admin_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def product_new():
    if request.method == 'POST':
        date, erori = _proces_formular(request.form)
        if erori:
            for e in erori:
                flash(e, 'error')
            return render_template(
                'admin/product_form.html',
                produs=request.form, mod='new', optiuni=OPTIUNI,
            )
        with get_db() as conn:
            conn.execute("""
                INSERT INTO products (nume, brand, categorie, pret, tip_ten, subton, nuanta,
                                      finish, ocazie, acoperire, ingrediente_cheie, vegan,
                                      cruelty_free, rating, descriere)
                VALUES (:nume, :brand, :categorie, :pret, :tip_ten, :subton, :nuanta,
                        :finish, :ocazie, :acoperire, :ingrediente_cheie, :vegan,
                        :cruelty_free, :rating, :descriere)
            """, date)
        flash(f'Produs "{date["nume"]}" adaugat cu succes', 'success')
        return redirect(url_for('admin.products'))
    return render_template(
        'admin/product_form.html', produs={}, mod='new', optiuni=OPTIUNI,
    )


@admin_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    with get_db() as conn:
        existent = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
    if not existent:
        flash('Produsul nu exista', 'error')
        return redirect(url_for('admin.products'))

    if request.method == 'POST':
        date, erori = _proces_formular(request.form)
        if erori:
            for e in erori:
                flash(e, 'error')
            return render_template(
                'admin/product_form.html',
                produs=request.form, mod='edit', id=product_id, optiuni=OPTIUNI,
            )
        with get_db() as conn:
            conn.execute("""
                UPDATE products
                SET nume = :nume, brand = :brand, categorie = :categorie, pret = :pret,
                    tip_ten = :tip_ten, subton = :subton, nuanta = :nuanta, finish = :finish,
                    ocazie = :ocazie, acoperire = :acoperire,
                    ingrediente_cheie = :ingrediente_cheie,
                    vegan = :vegan, cruelty_free = :cruelty_free,
                    rating = :rating, descriere = :descriere
                WHERE id = :id
            """, {**date, 'id': product_id})
        flash(f'Produs "{date["nume"]}" actualizat', 'success')
        return redirect(url_for('admin.products'))

    return render_template(
        'admin/product_form.html',
        produs=dict(existent), mod='edit', id=product_id, optiuni=OPTIUNI,
    )


@admin_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def product_delete(product_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT nume FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            flash(f'Produs "{row["nume"]}" sters', 'success')
        else:
            flash('Produsul nu exista', 'error')
    return redirect(url_for('admin.products'))


# ---------- Rapoarte ----------

@admin_bp.route('/reports')
@login_required
def reports_page():
    return render_template(
        'admin/reports.html',
        statistici=reports.statistici_generale(),
    )


@admin_bp.route('/api/reports/top-produse')
@login_required
def api_top_produse():
    return jsonify(reports.top_produse(limit=10))


@admin_bp.route('/api/reports/distributie-profiluri')
@login_required
def api_distributie():
    return jsonify(reports.distributie_profiluri())


@admin_bp.route('/api/reports/evolutie-zilnica')
@login_required
def api_evolutie():
    return jsonify(reports.evolutie_zilnica(zile=30))


# ---------- Webhook-uri n8n ----------

@admin_bp.route('/webhooks')
@login_required
def webhooks():
    filtru_status = request.args.get('status', '').strip()
    with get_db() as conn:
        if filtru_status:
            rows = conn.execute("""
                SELECT * FROM outbound_webhooks
                WHERE status = ?
                ORDER BY timestamp DESC LIMIT 200
            """, (filtru_status,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM outbound_webhooks
                ORDER BY timestamp DESC LIMIT 200
            """).fetchall()

        statistici = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS succes,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS erori,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) AS sarite
            FROM outbound_webhooks
        """).fetchone()

    import config
    return render_template(
        'admin/webhooks.html',
        webhooks=rows,
        statistici=dict(statistici),
        filtru=filtru_status,
        webhook_configurat=bool(config.N8N_WEBHOOK_URL),
        webhook_url=config.N8N_WEBHOOK_URL,
    )


# ---------- Validare formular ----------

def _proces_formular(form) -> tuple[dict, list[str]]:
    """Curata datele din formular si valideaza. Returneaza (dict, lista_erori)."""
    erori = []
    nume = form.get('nume', '').strip()
    brand = form.get('brand', '').strip()
    categorie = form.get('categorie', '').strip()

    if not nume:
        erori.append('Numele produsului este obligatoriu')
    if not brand:
        erori.append('Brand-ul este obligatoriu')
    if not categorie:
        erori.append('Categoria este obligatorie')

    try:
        pret = float(form.get('pret', 0) or 0)
        if pret < 0:
            erori.append('Pretul nu poate fi negativ')
    except ValueError:
        erori.append('Pretul trebuie sa fie un numar')
        pret = 0.0

    try:
        rating = float(form.get('rating', 4.0) or 4.0)
        if not (0 <= rating <= 5):
            erori.append('Rating-ul trebuie sa fie intre 0 si 5')
    except ValueError:
        erori.append('Rating-ul trebuie sa fie un numar')
        rating = 4.0

    date = {
        'nume': nume,
        'brand': brand,
        'categorie': categorie,
        'pret': pret,
        'tip_ten': form.get('tip_ten', 'toate').strip() or 'toate',
        'subton': form.get('subton', 'toate').strip() or 'toate',
        'nuanta': form.get('nuanta', 'toate').strip() or 'toate',
        'finish': form.get('finish', 'natural').strip() or 'natural',
        'ocazie': form.get('ocazie', 'zi').strip() or 'zi',
        'acoperire': form.get('acoperire', 'toate').strip() or 'toate',
        'ingrediente_cheie': form.get('ingrediente_cheie', '').strip(),
        'vegan': form.get('vegan', 'Nu').strip() or 'Nu',
        'cruelty_free': form.get('cruelty_free', 'Nu').strip() or 'Nu',
        'rating': rating,
        'descriere': form.get('descriere', '').strip(),
    }
    return date, erori
