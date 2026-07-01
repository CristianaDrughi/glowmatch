# Fragmente de cod pentru lucrare — frontend + flux end-to-end

Continuarea fisierului [FRAGMENTE_COD_LUCRARE.md](FRAGMENTE_COD_LUCRARE.md), pentru
sectiunile „Componente frontale" si „Fluxul de date end-to-end".

---

## ⚠️ Corectie necesara in text: Bootstrap NU este folosit

Textul spune „un strat de stilizare bazat pe Bootstrap". In cod **nu exista Bootstrap**
nicaieri — [base.html](templates/base.html#L7) incarca doar `style.css` (CSS scris de tine).
Singurul CDN din tot proiectul e **Chart.js**, si doar in pagina de rapoarte admin
([admin/reports.html](templates/admin/reports.html#L6)).

**Recomandare:** inlocuieste fraza cu, de exemplu:
> „...cu un strat de stilizare propriu, scris in CSS (fara framework CSS extern)."

Asa eviti o intrebare incomoda la sustinere si afirmatia devine adevarata. (Daca
*vrei* totusi Bootstrap, ti-l pot adauga — dar nu e nevoie, CSS-ul tau acopera tot.)

---

## 1. `base.html` — scheletul comun (mostenire de sabloane Jinja2)

Sursa: [base.html:1-39](templates/base.html#L1-L39) (trunchiat)

```html
<!DOCTYPE html>
<html lang="ro">
<head>
    <title>{% block title %}Recomandari{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body{% if activ %} class="page-{{ activ }}"{% endif %}>
    <nav class="site-nav"> ... </nav>
    <main>
        {% block content %}{% endblock %}   <!-- aici se randeaza paginile copil -->
    </main>
    <footer> ... </footer>
</body>
</html>
```
> *Legenda sugerata:* „Sablonul de baza: scheletul comun peste care se randeaza,
> prin `{% block content %}`, fiecare pagina individuala."
> **De ce:** arata exact mecanismul de mostenire Jinja2 (`block title` / `block content`).

---

## 2. `analiza_foto.html` — pagina copil (mosteneste scheletul)

Sursa: [analiza_foto.html:1-5](templates/analiza_foto.html#L1-L5)

```html
{% extends "base.html" %}                 {# reutilizeaza scheletul din base.html #}

{% block title %}Analiza foto AI &middot; Recomandari{% endblock %}

{% block content %}
  <!-- continutul specific paginii de incarcare a fotografiei -->
{% endblock %}
```
> **De ce:** completeaza fragmentul anterior — se vede cum o pagina concreta umple
> blocurile definite in base.html (`extends` + `block`).

---

## 3. Previzualizare imagine + indicator de procesare (JavaScript, fara framework)

Sursa: [analiza_foto.html:61-80](templates/analiza_foto.html#L61-L80) (trunchiat)

```javascript
// Cand utilizatorul alege o poza: afisam numele, butonul si o PREVIZUALIZARE.
inputPoza.addEventListener('change', function () {
    const fisier = inputPoza.files[0];
    numeFisier.textContent = 'Poza aleasa: ' + fisier.name;
    btnAnaliza.hidden = false;
    // Preview citit LOCAL, nu se trimite nicaieri pana la submit.
    const reader = new FileReader();
    reader.onload = (e) => { preview.src = e.target.result; preview.hidden = false; };
    reader.readAsDataURL(fisier);
});

// La trimitere: aratam spinner-ul si dezactivam butonul (evitam double-click).
document.getElementById('form-analiza').addEventListener('submit', function () {
    btnAnaliza.disabled = true;
    spinner.hidden = false;
});
```
> *Legenda sugerata:* „Previzualizarea imaginii si indicatorul de procesare,
> implementate in JavaScript nativ (`FileReader`), fara cadru suplimentar."
> **De ce:** sustine direct fraza despre „previzualizare a imaginii si un indicator
> de procesare pe durata analizei" + „JavaScript fara cadru suplimentar".

---

## 4. Tratarea erorilor — pagina prietenoasa + handler-ele server

**Fragment A — sablonul de eroare (un mesaj clar in loc de pagina tehnica).**
Sursa: [error.html:5-10](templates/error.html#L5-L10)

```html
{% block content %}
<section class="form-card" style="text-align: center;">
    <h2>Hopa, ceva n-a mers</h2>
    <p class="muted">{{ mesaj or 'A aparut o eroare neasteptata. Te rugam sa reincerci.' }}</p>
    <p><a href="{{ url_for('index') }}" class="btn-secondary">Inapoi la pagina principala</a></p>
</section>
{% endblock %}
```

**Fragment B — handler-ele din app.py care randeaza pagina de mai sus.**
Sursa: [app.py:231-247](app.py#L231-L247)

```python
@app.errorhandler(404)
def pagina_inexistenta(_e):
    return render_template('error.html', mesaj='Pagina cautata nu exista.'), 404

@app.errorhandler(413)   # fisier prea mare (peste MAX_CONTENT_LENGTH = 10 MB)
def fisier_prea_mare(_e):
    return render_template('error.html',
        mesaj='Fisierul e prea mare (maxim 10 MB). Incearca o poza mai mica.'), 413

@app.errorhandler(500)
def eroare_interna(_e):
    return render_template('error.html',
        mesaj='A aparut o eroare interna. Te rugam sa reincerci.'), 500
```
> **De ce:** acopera exact cele trei cazuri din text (adrese inexistente, fisier
> prea mare, eroare interna). A = ce vede utilizatorul, B = cum e produs.

---

## 5. Protectia datelor — se logheaza doar hash-ul, niciodata poza

Sursa: [db.py:117-129](db.py#L117-L129) (trunchiat)

```python
def logheaza_extractie(profil, image_hash):
    """Salveaza atributele extrase dintr-o analiza foto.
    NU stocheaza poza - doar un hash pentru audit."""
    atribute = ['ton', 'subton', 'culoare_ochi', 'culoare_par', 'ITA']
    with get_db() as conn:
        for atr in atribute:
            if atr in profil and profil[atr] is not None:
                conn.execute(
                    "INSERT INTO extraction_log (attribute_name, extracted_value, "
                    "confidence_score, image_hash) VALUES (?, ?, ?, ?)",
                    (atr, str(profil[atr]), None, image_hash),
                )
```
> **De ce:** dovada ca „in jurnalul de extragere se retine doar un hash, niciodata
> imaginea". (Observa ca nu se salveaza nici email-ul alaturi de trasaturi.)

---

## 6. FLUXUL END-TO-END — ruta completa /analiza-foto (figura 3.1 in cod)

Acesta e cel mai bun fragment pentru sectiunea de flux: intr-un singur loc se vede
tot lantul + separarea raspuns sincron / ramura asincrona.
Sursa: [app.py:79-141](app.py#L79-L141) (trunchiat semnificativ)

```python
@app.route('/analiza-foto', methods=['GET', 'POST'])
def analiza_foto():
    # ... validari fisier (tip imagine, ne-gol) ...

    poza_bytes = fisier.read()                                   # in memorie
    rezultat = vision.extract_profile_from_bytes(poza_bytes)     # (1) VISION
    if not rezultat.get('ok'):
        return render_template('analiza_foto.html', eroare=...)

    # (2) AUDIT: logam atributele + hash-ul pozei (NU poza in sine)
    logheaza_extractie(rezultat, hashlib.sha256(poza_bytes).hexdigest())

    # (3) Profilul extras devine 'preferinte' pentru motorul de recomandare
    preferinte = {'tip_produs': 'makeup', 'nuanta': rezultat['ton'],
                  'subton': rezultat['subton']}
    if rezultat.get('culoare_ochi') != 'unknown':
        preferinte['suited_eye_color'] = rezultat['culoare_ochi']

    # (4) Acelasi flux comun: recomanda + (daca e email) trimite la n8n
    return _genereaza_recomandari(preferinte, request.form.get('email', '').strip(),
                                  inapoi='analiza_foto', analiza=rezultat)
```

Si „inima" fluxului, unde se vede **separarea sincron / asincron** (din `_genereaza_recomandari`):
Sursa: [app.py:205-228](app.py#L205-L228) (trunchiat)

```python
def _genereaza_recomandari(preferinte, email, inapoi, analiza=None):
    df = incarca_produse()
    rezultate, log_id = recomanda(preferinte, df)        # SINCRON -> recommender.py

    if email:                                            # ASINCRON -> n8n (fir separat)
        payload = _construieste_payload(email, preferinte, produse, log_id)
        webhook_dispatcher.trimite_webhook(payload, email=email, log_id=log_id)

    return render_template('results.html', produse=produse, ...)  # raspuns imediat
```
> *Legenda sugerata:* „Ruta /analiza-foto leaga toate componentele; ramura de
> automatizare (n8n) ruleaza pe un fir separat, fara a intarzia raspunsul afisat."
> **De ce:** este figura 3.1 transpusa in cod — pasii (1)-(4) + separarea
> sincron (recomandarea afisata) / asincron (email-ul prin n8n).

---

## Recomandare de selectie (frontend + flux)

| Prioritate | Fragment | Ce demonstreaza |
|---|---|---|
| 1 | §6 ruta /analiza-foto + `_genereaza_recomandari` | fluxul end-to-end + sincron/asincron (= figura 3.1) |
| 2 | §3 JavaScript preview + spinner | UX-ul descris (previzualizare + indicator) |
| 3 | §1 + §2 base.html + extends | mostenirea de sabloane Jinja2 |
| 4 | §4 tratarea erorilor (A sau B) | paginile de eroare prietenoase |
| 5 | §5 logheaza_extractie | protectia datelor (doar hash) |

Daca spatiul e mic: pune **§6** (fluxul) si **§3** (UX-ul) — sunt cele mai
specifice si mai „vizibile" pentru cititor.
