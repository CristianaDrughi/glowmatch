# GlowMatch — Sistem de recomandare produse de makeup & skincare

Aplicatie web (Flask) de licenta care recomanda produse cosmetice pe baza unui
profil de ten, folosind un algoritm **rule-based cu scoring ponderat**. Include:

- **Analiza foto cu computer vision** (`vision.py`): detecteaza din poza tonul
  pielii (metrica **ITA°**, Chardon et al. 1991), subtonul, culoarea ochilor si
  a parului — folosind OpenCV + MediaPipe. Poza este procesata **in memorie**,
  nu se salveaza pe disc (confidentialitate).
- **Motor de recomandare** (`recommender.py`): filtre dure (categorie, buget,
  vegan, cruelty-free) + scoring ponderat pe 13+ atribute.
- **Catalog** de 754 produse (makeup + skincare) in SQLite.
- **Integrare n8n** (agentic AI): la cerere, trimite recomandarile pe email
  printr-un workflow n8n (Webhook → AI Agent Gemini → Send Email), securizat cu
  token Bearer.
- **Zona de admin** pentru gestionarea catalogului si rapoarte.

## Cerinte

- **Python 3.12** (obligatoriu — MediaPipe nu suporta 3.13+)
- Pachetele din `requirements.txt`

## Instalare

```bash
# 1. Creeaza un mediu virtual cu Python 3.12
py -3.12 -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Instaleaza dependentele
pip install -r requirements.txt
```

## Initializare baza de date (o singura data)

Baza de date (`data/app.db`) NU este in repo (poate contine date personale din
loguri). Se reconstruieste din CSV-urile comise (`data/products.csv` cu cele 754
produse + `data/test_cases.csv`):

```bash
venv\Scripts\python.exe seed_db.py            # parola admin generata aleatoriu
# sau: python seed_db.py parola_mea           # parola admin la alegere
```
Scriptul afiseaza parola admin generata - salveaz-o.

## Rulare

```bash
venv\Scripts\python.exe app.py
```
Aplicatia porneste pe **http://localhost:5000**.

## Variabile de mediu (optionale — pentru emailul prin n8n)

| Variabila | Rol |
|-----------|-----|
| `N8N_WEBHOOK_URL` | URL-ul webhook-ului n8n. Gol = emailul e sarit (logat `skipped`). |
| `N8N_WEBHOOK_TOKEN` | Token Bearer trimis catre webhook (Header Auth in n8n). |
| `FLASK_SECRET_KEY` | Cheia de sesiune Flask (in productie). |

Daca nu sunt setate, aplicatia ruleaza normal — doar emailul nu se trimite.

## Structura

| Fisier | Rol |
|--------|-----|
| `app.py` | Rutele Flask (pagini + analiza foto) |
| `vision.py` | Analiza foto (ITA°, ochi, par) |
| `recommender.py` | Algoritmul de recomandare rule-based |
| `db.py` | Schema + acces SQLite |
| `webhook_dispatcher.py` | Trimitere asincrona catre n8n |
| `evaluate_pipeline.py` | Evaluarea acuratetei analizei foto |
| `validate_catalog.py` | Validarea catalogului |
| `data/known_issues.md` | Limitari cunoscute documentate |

## Acuratete masurata (analiza foto, set de 20 poze)

| Atribut | Acuratete |
|---------|-----------|
| Ton ten (ITA°) | 100% |
| Culoare par | 72% |
| Culoare ochi | 63% |
| Subton | 40% (limitare documentata) |

Forma fetei a fost testata, dar exclusa (rezultat negativ — vezi `known_issues.md`).
