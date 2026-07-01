# Structura aplicatiei — ce face fiecare fisier

Acest document explica, pe scurt si pe intelesul tuturor, rolul fiecarui fisier
cu cod din aplicatie. E util pentru lucrarea de licenta (capitolul de arhitectura)
si pentru a te orienta rapid in proiect.

GlowMatch este o aplicatie web Flask care:
1. analizeaza o poza a fetei (computer vision) si extrage tonul tenului, subtonul,
   culoarea ochilor si a parului;
2. recomanda produse de makeup / skincare pe baza unui motor de reguli + scoring;
3. (optional) trimite recomandarile pe email printr-un flux automat n8n.

---

## 1. Inima aplicatiei (codul care ruleaza in productie)

Acestea sunt fisierele care formeaza aplicatia propriu-zisa, pe care o vezi in browser.

### `app.py` — punctul de pornire al aplicatiei web
Creeaza aplicatia Flask si defineste toate paginile (rutele):
- `/` — pagina principala (home)
- `/analiza-foto` — incarci o poza, ruleaza computer vision-ul si genereaza recomandari
- `/recomandari` — formular pentru recomandari de **makeup**
- `/skincare` — formular pentru recomandari de **skincare**
- `/ghid` — pagina de ghid
Tot aici se face legatura intre toate piesele: cand urci o poza, cheama `vision.py`
sa o analizeze, apoi `recommender.py` sa scoata produsele, iar daca ai dat un email,
`webhook_dispatcher.py` trimite rezultatul catre n8n. Poza **nu se salveaza pe disc**
(se proceseaza in memorie, din motive de GDPR). Tot aici sunt si paginile de eroare
prietenoase (404, 413 — fisier prea mare, 500).

### `config.py` — setarile aplicatiei
Un singur loc pentru valorile configurabile: URL-ul webhook-ului n8n, token-ul de
securitate, cheia secreta Flask. Toate se pot suprascrie din variabile de mediu.

### `db.py` — baza de date
Defineste **schema** bazei de date SQLite (tabelele) si ofera functia `get_db()`
prin care restul codului vorbeste cu baza de date. Tabelele principale:
- `products` — catalogul de produse
- `recommendations_log` + `recommendation_products` — istoricul recomandarilor (pentru rapoarte)
- `admin_users` — conturile de administrator
- `outbound_webhooks` — jurnalul apelurilor catre n8n
- `extraction_log` — ce a detectat AI-ul din fiecare poza (fara sa pastreze poza, doar un hash)
- `test_cases` — pozele de test cu etichetele lor reale (pentru evaluare)
La pornire, `init_db()` se asigura ca toate tabelele exista si adauga coloane noi
daca baza de date e mai veche (migrare automata).

### `recommender.py` — motorul de recomandare (piesa centrala a lucrarii)
Algoritmul rule-based + scoring ponderat:
1. **Filtre obligatorii** (hard filters): tip produs, categorie, buget, vegan,
   cruelty-free — produsele care nu trec sunt eliminate.
2. **Scoring ponderat**: fiecare criteriu care se potriveste aduce puncte. Criteriile
   importante pentru piele (tip ten, subton) cantaresc mai mult decat cele estetice.
   Ingredientele si problemele pielii adauga puncte incremental.
3. Produsele se sorteaza dupa scor, iar la egalitate dupa rating.
Fiecare recomandare e logata in baza de date pentru rapoarte si evaluare.

### `vision.py` — analiza foto (computer vision)
Primeste o poza si extrage profilul tenului:
- Detecteaza fata cu **MediaPipe**, citeste culoarea pielii de pe obraji si frunte.
- Calculeaza **ITA°** (Individual Typology Angle) — metrica standard din dermatologie,
  citabila in lucrare — si clasifica tonul in: deschis / mediu / inchis.
- Estimeaza subtonul (cald / rece / neutru / olive), culoarea ochilor (blue/green/
  brown/hazel) si culoarea parului (black/brunette/blonde/gray).
- Forma fetei (`extract_face_shape`) e **experimentala si NU se foloseste in productie**
  — a fost un rezultat negativ documentat in lucrare (acuratete sub baseline).
Are si o functie `evaluate_folder()` cu care masori acuratetea pe poze etichetate.

### `webhook_dispatcher.py` — trimiterea catre n8n (email automat)
Daca utilizatorul a dat un email, aceasta functie trimite recomandarile catre
webhook-ul n8n **in fundal** (pe un thread separat, ca sa nu blocheze browser-ul).
Indiferent de rezultat, fiecare apel e logat (success / error / skipped). Daca
webhook-ul nu e configurat, apelul e marcat ca "skipped" (util in dezvoltare).

### `auth.py` — autentificare admin
Login / logout pentru zona de administrare, folosind Flask-Login. Parolele sunt
verificate cu hash securizat (werkzeug / PBKDF2).

### `admin.py` — panoul de administrare
Tot ce tine de zona `/admin` (necesita login):
- **CRUD produse**: adaugare, editare, stergere, cautare in catalog.
- **Rapoarte**: rute API care intorc JSON pentru graficele din dashboard.
- **Webhook-uri**: pagina care arata jurnalul apelurilor catre n8n.

### `reports.py` — interogarile pentru rapoarte
Functii SQL care calculeaza statistici pentru dashboard-ul admin: top produse
recomandate, distributia profilurilor utilizatorilor, evolutia zilnica, ce a
detectat AI-ul din poze, calitatea catalogului, cele mai cerute categorii/probleme
si produsele care nu au fost niciodata recomandate ("dead stock").

---

## 2. Scripturi pentru date (le rulezi o data, manual, din terminal)

Acestea **nu** fac parte din aplicatia care ruleaza in browser — sunt unelte de
pregatire a datelor. Le rulezi cand configurezi proiectul sau cand actualizezi catalogul.

### `seed_db.py` — reconstruieste baza de date
Cel mai important script de setup. Reconstruieste `data/app.db` din fisierele CSV
din repo (catalogul **nu** se tine in git ca baza de date binara). Il rulezi **o data
dupa ce clonezi repo-ul**. Creeaza si contul de admin.

### `import_excel.py` — importa produse din Excel
Citeste produsele dintr-un fisier Excel (foile Makeup + Skincare), normalizeaza
valorile (coduri tip ten, separatori) si le baga in tabela `products`.

### `import_poze.py` — potriveste pozele cu produsele
Pentru fiecare poza din folderul "Poze produse", gaseste produsul cu numele cel mai
asemanator, copiaza poza in `static/product_images/` si o leaga de produs.

### `link_images.py` — leaga pozele descarcate de produse
Varianta care leaga pozele descarcate automat (din `images/`) de produsele din DB,
pe baza unui CSV.

### `eticheteaza_culori.py` — eticheteaza produsele pe ochi/par
Completeaza automat campurile `suited_eye_color` / `suited_hair_color` pe baza unor
**reguli de teoria culorilor** (ex. fardul de pleoape se potriveste cu culoarea ochilor,
rujul cu culoarea parului). Restul produselor raman "toate" (universale).

---

## 3. Scripturi de validare, testare si evaluare (pentru lucrare)

Acestea genereaza cifrele si verificarile care apar in capitolul de rezultate.

### `validate_catalog.py` — verifica integritatea catalogului
Verifica daca produsele au campurile obligatorii completate, preturi/rating valide,
valori corecte, si analizeaza echilibrul catalogului pe categorii si tonuri (detecteaza bias).

### `test_recommendation.py` — test pe profiluri sintetice
Ruleaza motorul de recomandare pe cateva profiluri scrise manual ca sa verifici ca
rezultatele au sens si ca timpul de executie e sub 1 secunda.

### `eval_h1.py` — baza comuna pentru evaluarea H1 (precision@5)
Contine cele 10 profiluri de test + cele 2 algoritme (rule-based si random cu seed fix).
E importat de scripturile de mai jos ca rezultatele sa fie identice intre ele.

### `genereaza_template_h1.py` — creeaza CSV-ul de etichetat
Genereaza fisierul CSV (prin "pooling") pe care il completezi manual cu Y/N
(produs relevant / nu) pentru fiecare profil. Etichetare oarba (nu stii ce algoritm
a produs fiecare produs).

### `eval_precision_at_5.py` — calculeaza precision@5
Dupa ce ai etichetat CSV-ul, calculeaza precision@5 pentru rule-based vs random si
genereaza sinteza + graficul (verdictul H1).

### `eval_h1_fond.py` — H1 focalizat pe fond de ten
Aceeasi evaluare, dar concentrata pe fondul de ten, unde alegerea nuantei conteaza cel
mai mult. Relevanta e obiectiva (nuanta fondului include tonul profilului).

### `evaluate_pipeline.py` — evalueaza analiza foto (vision.py)
Ruleaza vision.py pe pozele de test, compara cu etichetele reale (notate manual) si
raporteaza acuratetea pe ton, subton si culoarea ochilor + matrice de confuzie.

### `populate_test_cases.py` — incarca ground truth-ul in DB
Pune in tabela `test_cases` etichetele reale (notate vizual) pentru pozele de test 3-22.

### `calibrare_ten.py` — script temporar de calibrare
Afiseaza ITA + valorile Lab pentru fiecare poza de test, ca sa gasesti pragurile bune
care separa tenul olive de cel deschis. Nu face parte din aplicatie.

### `compara_poze.py` — verifica ce produse nu au poza
Compara produsele din DB cu cele dintr-un Excel cu poze si raporteaza ce produse nu au
inca poza.

---

## 4. Foldere

### `templates/` — paginile HTML (Jinja2)
- `base.html` — scheletul comun al paginilor publice
- `home.html`, `ghid.html` — paginile statice
- `analiza_foto.html` — pagina de upload poza
- `recomandari.html`, `skincare.html` — formularele de recomandare
- `results.html` — pagina cu produsele recomandate
- `error.html` — pagina de eroare
- `admin/` — paginile zonei de administrare (login, lista produse, formular produs,
  rapoarte, webhook-uri)

### `static/` — fisiere statice
- `style.css` — stilurile aplicatiei
- `product_images/`, `images/` — pozele produselor

### `data/` — datele aplicatiei
- `app.db` — baza de date SQLite (generata de `seed_db.py`, **nu** e in git)
- `products.csv`, `test_cases.csv` — sursa de date din care se reconstruieste DB-ul
- `known_issues.md` — limitarile cunoscute (foarte util pentru lucrare)

### `evaluation/` — rezultatele evaluarii
CSV-urile, sinteza (`summary_h1.md`) si graficele generate de scripturile de evaluare.

### `venv/` — mediul Python
Bibliotecile instalate (Flask, OpenCV, MediaPipe, pandas etc.). **Nu** e cod scris de tine.

---

## Cum se leaga totul (flux simplificat)

```
Utilizator urca poza
        │
        ▼
   app.py (ruta /analiza-foto)
        │
        ├──► vision.py        → extrage ton, subton, ochi, par din poza
        │
        ├──► recommender.py   → filtreaza + scoreaza produsele din db.py
        │
        └──► webhook_dispatcher.py → (daca e email) trimite la n8n → email
        │
        ▼
   results.html (produsele recomandate)
```

Datele sunt in `data/app.db`, construit din CSV cu `seed_db.py`. Zona de admin
(`admin.py` + `auth.py`) gestioneaza catalogul si arata rapoartele din `reports.py`.
