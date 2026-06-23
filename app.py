import hashlib
from datetime import datetime

from flask import Flask, render_template, request
from flask_login import LoginManager

import config
import vision
import webhook_dispatcher
from admin import admin_bp
from auth import auth_bp, load_user
from db import init_db, logheaza_extractie
from recommender import incarca_produse, recomanda

INGREDIENTE_DISPONIBILE = [
    'acid hialuronic',
    'vitamina C',
    'vitamina E',
    'niacinamida',
    'peptide',
    'ulei de argan',
    'ulei de jojoba',
    'SPF',
    'retinol',
    'acid salicilic',
    'acid glicolic',
    'acid lactic',
    'acid azelaic',
    'ceramide',
    'centella asiatica',
    'panthenol',
    'squalane',
    'aloe vera',
    'zinc',
    'colagen',
    'bakuchiol',
    'ulei de tea tree',
]

PROBLEME_PIELE = [
    'acnee fungica',
    'acnee cosmetica',
    'pori inchisi',
    'pori largi',
    'puncte albe',
    'puncte negre',
    'textura',
    'bariera pielii distrusa',
    'filamente sebacee',
    'inbatranit',
    'inflamatii',
    'semne postacneice',
]


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY

    # Limita de marime upload (poze): 10 MB. Peste -> eroare 413 tratata mai jos.
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

    # Asigura ca toate tabelele exista (idempotent prin IF NOT EXISTS)
    init_db()

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Trebuie sa te autentifici pentru a accesa zona admin.'
    login_manager.login_message_category = 'error'
    login_manager.user_loader(load_user)

    app.register_blueprint(auth_bp, url_prefix='/admin')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        return render_template('home.html')

    @app.route('/analiza-foto', methods=['GET', 'POST'])
    def analiza_foto():
        if request.method == 'GET':
            return render_template('analiza_foto.html', activ='analiza')

        # POST: utilizatorul a urcat o poza pentru analiza (CV + ITA°).
        fisier = request.files.get('poza')
        if not fisier or not fisier.filename:
            return render_template(
                'analiza_foto.html', activ='analiza',
                eroare='Te rog alege o poza inainte de a trimite.',
            )

        # Validare tip fisier (acceptam doar imagini).
        if fisier.mimetype and not fisier.mimetype.startswith('image/'):
            return render_template(
                'analiza_foto.html', activ='analiza',
                eroare='Fisierul ales nu este o imagine. Incarca o poza JPG sau PNG.',
            )

        # Analiza ruleaza in memorie, pe bytes - poza nu este salvata pe disc (GDPR).
        poza_bytes = fisier.read()
        if not poza_bytes:
            return render_template(
                'analiza_foto.html', activ='analiza',
                eroare='Fisierul pare gol. Incearca alta poza.',
            )
        try:
            rezultat = vision.extract_profile_from_bytes(poza_bytes)
        except Exception:
            return render_template(
                'analiza_foto.html', activ='analiza',
                eroare='Nu am putut procesa poza. Incearca o poza JPG/PNG clara.',
            )
        if not rezultat.get('ok'):
            return render_template(
                'analiza_foto.html', activ='analiza',
                eroare=rezultat.get('error', 'Nu am putut analiza poza.')
                + ' Incearca o poza clara, la lumina naturala, cu fata vizibila.',
            )

        # Audit: logam atributele extrase (cu hash-ul pozei, NU poza in sine).
        logheaza_extractie(rezultat, hashlib.sha256(poza_bytes).hexdigest())

        # Datele extrase din poza devin preferinte pentru motorul de recomandare.
        # vision.py returneaza 'ton' (deschis/mediu/inchis) -> mapat la 'nuanta'.
        preferinte = {
            'tip_produs': 'makeup',
            'nuanta': rezultat['ton'],
            'subton': rezultat['subton'],
        }
        # Culoarea ochilor/parului influenteaza recomandarile (pondere mica) doar
        # daca au fost detectate (nu 'unknown'). Vezi suited_* in recommender.
        if rezultat.get('culoare_ochi') and rezultat['culoare_ochi'] != 'unknown':
            preferinte['suited_eye_color'] = rezultat['culoare_ochi']
        if rezultat.get('culoare_par') and rezultat['culoare_par'] != 'unknown':
            preferinte['suited_hair_color'] = rezultat['culoare_par']
        # Reutilizam fluxul comun: ruleaza recomandarile si, daca e email, le
        # trimite pe email prin n8n (la fel ca formularul manual).
        return _genereaza_recomandari(
            preferinte, request.form.get('email', '').strip(),
            inapoi='analiza_foto', analiza=rezultat,
        )

    @app.route('/ghid')
    def ghid():
        return render_template('ghid.html', activ='ghid')

    @app.route('/recomandari', methods=['GET', 'POST'])
    def recomandari():
        """Recomandari de makeup (profil ten + trasaturi faciale + produs)."""
        if request.method == 'GET':
            df = incarca_produse()
            df_makeup = df[df['tip_produs'] == 'makeup'] if 'tip_produs' in df.columns else df
            categorii = sorted(df_makeup['categorie'].unique())
            return render_template(
                'recomandari.html',
                categorii=categorii,
                activ='makeup',
            )

        preferinte = {
            'tip_produs': 'makeup',
            'tip_ten': request.form.get('tip_ten'),
            'subton': request.form.get('subton'),
            'nuanta': request.form.get('nuanta'),
            'forma': request.form.get('forma'),
            'contrast': request.form.get('contrast'),
            'greutate_vizuala': request.form.get('greutate_vizuala'),
            'forma_ochilor': request.form.get('forma_ochilor'),
            'pozitie_ochi_vertical': request.form.get('pozitie_ochi_vertical'),
            'pozitie_ochi_adancime': request.form.get('pozitie_ochi_adancime'),
            'pozitie_ochi_distanta': request.form.get('pozitie_ochi_distanta'),
            'forma_buzelor': request.form.get('forma_buzelor'),
            'ocazie': request.form.get('ocazie'),
            'finish': request.form.get('finish'),
            'acoperire': request.form.get('acoperire'),
            'baza': request.form.get('baza'),
            'categorie': request.form.get('categorie'),
            'buget': request.form.get('buget') or None,
        }
        return _genereaza_recomandari(preferinte, request.form.get('email', '').strip(),
                                      inapoi='recomandari')

    @app.route('/skincare', methods=['GET', 'POST'])
    def skincare():
        """Recomandari de skincare (tip ten + probleme + ingrediente + etica)."""
        if request.method == 'GET':
            return render_template(
                'skincare.html',
                ingrediente=INGREDIENTE_DISPONIBILE,
                probleme=PROBLEME_PIELE,
                activ='skincare',
            )

        preferinte = {
            'tip_produs': 'skincare',
            'tip_ten': request.form.get('tip_ten'),
            'probleme': request.form.getlist('probleme'),
            'ingrediente_cheie': request.form.getlist('ingrediente_cheie'),
            'doar_vegan': request.form.get('doar_vegan') == 'on',
            'doar_cruelty_free': request.form.get('doar_cruelty_free') == 'on',
        }
        return _genereaza_recomandari(preferinte, request.form.get('email', '').strip(),
                                      inapoi='skincare')

    def _genereaza_recomandari(preferinte: dict, email: str, inapoi: str, analiza: dict | None = None):
        df = incarca_produse()
        rezultate, log_id = recomanda(preferinte, df)
        produse = rezultate.to_dict('records')

        # Daca utilizatorul a furnizat email, declanseaza workflow-ul n8n
        # (Sprint 9-10). In dezvoltare (fara N8N_WEBHOOK_URL), apelul e logat
        # ca 'skipped' - util pentru a vedea ce s-ar fi trimis.
        status_webhook = None
        if email:
            payload = _construieste_payload(email, preferinte, produse, log_id)
            status_webhook = webhook_dispatcher.trimite_webhook(
                payload, email=email, log_id=log_id,
            )

        return render_template(
            'results.html',
            produse=produse,
            preferinte=preferinte,
            email=email,
            status_webhook=status_webhook,
            inapoi=inapoi,
            analiza=analiza,
        )

    # --- Tratare erori (pagini prietenoase in loc de stack trace) ---
    @app.errorhandler(404)
    def pagina_inexistenta(_e):
        return render_template('error.html', mesaj='Pagina cautata nu exista.'), 404

    @app.errorhandler(413)
    def fisier_prea_mare(_e):
        return render_template(
            'error.html',
            mesaj='Fisierul e prea mare (maxim 10 MB). Incearca o poza mai mica.',
        ), 413

    @app.errorhandler(500)
    def eroare_interna(_e):
        return render_template(
            'error.html',
            mesaj='A aparut o eroare interna. Te rugam sa reincerci.',
        ), 500

    return app


def _construieste_payload(email: str, preferinte: dict, produse: list, log_id: int | None) -> dict:
    """Construieste payload-ul JSON trimis catre n8n.

    Format documentat in capitolul 3.6 al lucrarii.
    """
    pref_curate = {
        k: v for k, v in preferinte.items()
        if v not in (None, '', 'oricare', False, [])
    }
    return {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'log_id': log_id,
        'email': email,
        'preferinte': pref_curate,
        'produse_recomandate': [
            {
                'id': int(p['id']),
                'nume': p['nume'],
                'brand': p['brand'],
                'categorie': p['categorie'],
                'pret': float(p['pret']),
                'rating': float(p['rating']),
                'descriere': p['descriere'],
            }
            for p in produse
        ],
    }


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
