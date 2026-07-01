# Fragmente de cod pentru lucrare (sectiunea de arhitectura)

Bucati scurte si reprezentative din fiecare componenta backend, alese ca sa
ilustreze exact afirmatiile din text. Fiecare are: locul in cod, o sugestie de
legenda (caption) si o nota cu motivul alegerii. Le poti copia direct.

---

## 1. `app.py` — orchestrarea componentelor

**Fragment A — handoff-ul intre module (cel mai reprezentativ pentru „orchestreaza").**
Sursa: [app.py:205-228](app.py#L205-L228)

```python
def _genereaza_recomandari(preferinte, email, inapoi, analiza=None):
    df = incarca_produse()
    rezultate, log_id = recomanda(preferinte, df)        # -> recommender.py
    produse = rezultate.to_dict('records')

    # Daca utilizatorul a furnizat email, declanseaza workflow-ul n8n.
    status_webhook = None
    if email:
        payload = _construieste_payload(email, preferinte, produse, log_id)
        status_webhook = webhook_dispatcher.trimite_webhook(   # -> n8n
            payload, email=email, log_id=log_id,
        )
    return render_template('results.html', produse=produse, ...)
```
> *Legenda sugerata:* „Functia de orchestrare: app.py cheama motorul de recomandare
> si, optional, declanseaza trimiterea catre fluxul de automatizare."
> **De ce:** intr-o singura functie se vede cum app.py leaga `recommender.py` de
> `webhook_dispatcher.py` — exact ideea de „orchestreaza celelalte componente".

**Fragment B — prelucrare in memorie, fara salvare pe disc (GDPR).**
Sursa: [app.py:99-107](app.py#L99-L107)

```python
# Analiza ruleaza in memorie, pe bytes - poza nu este salvata pe disc (GDPR).
poza_bytes = fisier.read()
if not poza_bytes:
    return render_template('analiza_foto.html', activ='analiza',
                           eroare='Fisierul pare gol. Incearca alta poza.')
rezultat = vision.extract_profile_from_bytes(poza_bytes)   # -> vision.py
```
> **De ce:** sustine direct fraza despre conformitatea GDPR. Scurt si la obiect.

---

## 2. `config.py` — configurare suprascrisa din variabile de mediu

Sursa: [config.py:13-28](config.py#L13-L28)

```python
# URL-ul complet al webhook-ului n8n (suprascris din variabila de mediu).
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', '').strip()

# Token secret trimis ca 'Authorization: Bearer <token>' catre n8n.
N8N_WEBHOOK_TOKEN = os.environ.get('N8N_WEBHOOK_TOKEN', '').strip()

# Cheia secreta Flask pentru session cookies.
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'licenta-makeup-...-2026')
```
> **De ce:** arata pattern-ul `os.environ.get(...)` = „separarea configuratiei de cod".

---

## 3. `db.py` — conexiune, schema si migrare automata

**Fragment A — functia de conectare (context manager).**
Sursa: [db.py:14-23](db.py#L14-L23)

```python
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
```
> **De ce:** „functia de conectare folosita de restul aplicatiei" — commit + close garantate.

**Fragment B — migrarea automata a schemei.**
Sursa: [db.py:151-163](db.py#L151-L163)

```python
def _migreaza(conn):
    """Adauga coloanele noi pe o tabela products deja existenta (idempotent)."""
    existente = {r['name'] for r in conn.execute("PRAGMA table_info(products)")}
    for coloana, definitie in COLOANE_NOI_PRODUCTS.items():
        if coloana not in existente:
            conn.execute(f"ALTER TABLE products ADD COLUMN {coloana} {definitie}")

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)   # CREATE TABLE IF NOT EXISTS ...
        _migreaza(conn)              # adauga coloanele lipsa
```
> **De ce:** sustine exact fraza despre „adauga automat coloanele lipsa ... fara
> interventie manuala". (Optional poti pune si 2-3 randuri din `SCHEMA` ca exemplu de tabel.)

---

## 4. `recommender.py` — motorul de recomandare (componenta centrala)

**Fragment A — ponderile (arata prioritatea pielii fata de estetica).**
Sursa: [recommender.py:25-37](recommender.py#L25-L37)

```python
PONDERI = {
    'tip_ten': 3,            # criterii critice pentru piele -> pondere mare
    'subton': 2,
    'nuanta': 2,
    'acoperire': 2,
    'contrast': 1,           # criterii estetice -> pondere mica
    'ocazie': 1,
    'finish': 1,
    'suited_eye_color': 1,   # din analiza foto (acuratete moderata) -> tiebreaker
    'suited_hair_color': 1,
}
```

**Fragment B — filtre obligatorii + scoring + sortare (esenta algoritmului).**
Sursa: [recommender.py:131-164](recommender.py#L131-L164) (trunchiat)

```python
def recomanda(preferinte, df, numar=5):
    rezultate = df.copy()

    # 1. FILTRE OBLIGATORII (hard filters)
    if preferinte.get('categorie') not in (None, 'oricare'):
        rezultate = rezultate[rezultate['categorie'] == preferinte['categorie']]
    if preferinte.get('buget'):
        rezultate = rezultate[rezultate['pret'] <= float(preferinte['buget'])]
    if preferinte.get('doar_vegan'):
        rezultate = rezultate[rezultate['vegan'] == 'Da']

    # 2. SCORING PONDERAT (fiecare criteriu potrivit aduce puncte)
    scoruri = [_scor(p, preferinte) for _, p in rezultate.iterrows()]
    rezultate = rezultate.assign(scor=[s for s, _ in scoruri])

    # 3. SORTARE descrescatoare dupa scor, apoi dupa rating (tiebreaker)
    return rezultate.sort_values(['scor', 'rating'], ascending=[False, False]).head(numar)
```
> **De ce:** se vad clar cele trei etape (filtre -> scoring -> sortare) intr-un singur loc.
> Detaliile raman in sectiunea 3.5, asa cum spui in text.

---

## 5. `vision.py` — analiza fotografiei (ITA°)

**Fragment A — calculul ITA° si clasificarea tonului (partea citabila).**
Sursa: [vision.py:170-179](vision.py#L170-L179)

```python
# MEDIANA pe canale = robusta la pixeli aberanti (umbre, fire de par)
median_bgr = np.median(pixeli, axis=0)
L, a, b = _bgr_la_lab_real(median_bgr)            # CIELAB real

# ITA = arctan((L* - 50) / b*) * 180/pi  (Chardon et al., 1991)
ita = float(np.degrees(np.arctan2(L - 50.0, b))) if b != 0 else 0.0

ton, subton = _ton_3(ita), _subton(a, b)          # deschis / mediu / inchis
```

**Fragment B — analiza din bytes, fara scriere pe disc.**
Sursa: [vision.py:428-432](vision.py#L428-L432)

```python
def extract_profile_from_bytes(image_bytes, white_balance=True):
    """Din bytes (upload Flask) - NU scrie poza pe disc."""
    arr = np.frombuffer(image_bytes, np.uint8)
    return _analyze_img(cv2.imdecode(arr, cv2.IMREAD_COLOR), white_balance)
```
> **De ce:** A = metrica obiectiva citabila (punctul forte stiintific); B = leaga de
> promisiunea GDPR din app.py.

---

## 6. `webhook_dispatcher.py` — trimitere pe fir de executie separat

Sursa: [webhook_dispatcher.py:79-104](webhook_dispatcher.py#L79-L104) (trunchiat)

```python
def trimite_webhook(payload, email='', log_id=None):
    url = config.N8N_WEBHOOK_URL
    if not url:                          # webhook neconfigurat -> 'skipped'
        _logheaza(log_id, email, '', payload, status='skipped', ...)
        return 'skipped'

    # Fir separat: nu blocheaza raspunsul HTTP catre browser.
    thread = threading.Thread(
        target=_executa_post, args=(log_id, email, payload, url, timeout),
        daemon=True,
    )
    thread.start()
    return 'dispatched'
```
> **De ce:** se vede atat firul de executie separat, cat si starea „skipped" cand
> webhook-ul nu e configurat — ambele mentionate in text.

---

## 7. `auth.py` — autentificare cu hash PBKDF2

Sursa: [auth.py:31-44](auth.py#L31-L44) (trunchiat)

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    row = conn.execute("SELECT * FROM admin_users WHERE username = ?",
                       (username,)).fetchone()
    # Parola NU se compara in clar: se verifica hash-ul PBKDF2.
    if row and check_password_hash(row['password_hash'], password):
        login_user(AdminUser(row))
        return redirect(url_for('admin.products'))
    flash('Username sau parola incorecta', 'error')
```
> **De ce:** `check_password_hash` = dovada ca parolele nu sunt stocate in clar.

---

## 8. `admin.py` — operatiune CRUD pe catalog (exemplu: adaugare produs)

Sursa: [admin.py:54-76](admin.py#L54-L76) (trunchiat)

```python
@admin_bp.route('/products/new', methods=['GET', 'POST'])
@login_required                                  # protejat de Flask-Login
def product_new():
    if request.method == 'POST':
        date, erori = _proces_formular(request.form)   # validare
        if erori:
            ...
            return render_template('admin/product_form.html', ...)
        with get_db() as conn:
            conn.execute("INSERT INTO products (nume, brand, categorie, pret, ...) "
                         "VALUES (:nume, :brand, :categorie, :pret, ...)", date)
        flash(f'Produs "{date["nume"]}" adaugat cu succes', 'success')
        return redirect(url_for('admin.products'))
```
> **De ce:** ilustreaza si `@login_required` (zona protejata), si validarea, si scrierea in DB.

---

## 9. `reports.py` — interogare agregata pentru rapoarte (exemplu)

Sursa: [reports.py:13-24](reports.py#L13-L24)

```python
def top_produse(limit=10):
    """Top N cele mai recomandate produse."""
    rows = conn.execute("""
        SELECT p.nume, p.brand, COUNT(*) AS nr_recomandari
        FROM recommendation_products rp
        JOIN products p ON p.id = rp.produs_id
        GROUP BY p.id
        ORDER BY nr_recomandari DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(r) for r in rows]
```
> **De ce:** un singur exemplu de raport (JOIN + GROUP BY) e suficient; restul
> rapoartelor folosesc acelasi tipar.

---

## Recomandare de selectie (daca spatiul e limitat)

Daca nu incapi toate, pune **doar cele 4 esentiale** (acopera ideile-cheie ale lucrarii):

| Prioritate | Fragment | Ce demonstreaza |
|---|---|---|
| 1 | `recommender.py` B (filtre+scoring+sortare) | componenta centrala |
| 2 | `vision.py` A (ITA°) | rigoare stiintifica, citabila |
| 3 | `app.py` A (orchestrarea) | cum se leaga modulele |
| 4 | `db.py` B (migrarea automata) | maturitatea stratului de date |

Restul (config, webhook, auth, admin, reports) le poti mentiona in text fara cod,
sau le pui in anexa.
