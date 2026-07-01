# Fragmente de cod — analiza foto (3.4), recomandare (3.5), n8n (3.6), evaluare (3.7-3.8)

Continuarea fisierelor [FRAGMENTE_COD_LUCRARE.md](FRAGMENTE_COD_LUCRARE.md) si
[FRAGMENTE_COD_FRONTEND.md](FRAGMENTE_COD_FRONTEND.md). Acelasi format: fragment
scurt + legenda sugerata + de ce e ales. La final, doua corecturi necesare in text.

---

## ⚠️ DOUA CORECTURI NECESARE IN TEXT (citeste intai)

Am comparat textul tau cu codul real ([vision.py](vision.py)) si cu
[known_issues.md](data/known_issues.md). Doua afirmatii **nu corespund** codului:

### A. Culoarea ochilor — numarul de categorii si acuratetea
- **Textul spune:** „redusa de la patru categorii la trei, prin eliminarea
  categoriei caprui-verzui" si „acuratete intre aproximativ 75 si 80 la suta".
- **Codul face:** `_categorie_ochi` returneaza **4 categorii** — `blue`, `green`,
  `brown`, **`hazel`** (caprui-verzui inca exista, [vision.py:199-206](vision.py#L199-L206)).
- **Acuratetea reala masurata:** **~63% (12/19)**, nu 75-80%
  ([known_issues.md, sectiunea ochi](data/known_issues.md#L49-L56)).
- **Ce a fost de fapt redus la 3:** la **par** s-a eliminat o categorie (`red`),
  nu la ochi. Probabil s-au incurcat cele doua in text.

### B. Culoarea parului — numarul de categorii
- **Textul spune:** „cinci categorii: negru, saten, blond, roscat si grizonant".
- **Codul face:** `_categorie_par` returneaza **4 categorii** — `black`, `brunette`,
  `blonde`, `gray`. **`red` (roscat) a fost ELIMINAT** si contopit cu `brunette`
  ([vision.py:304-316](vision.py#L304-L316), [known_issues.md:66-69](data/known_issues.md#L66-L69)).
- **Acuratetea „peste 70%" este corecta:** ~72% (13/18). ✅

**Recomandare:** reformuleaza astfel incat cifrele sa fie aparabile:
> Ochi: „...patru categorii (albastru, verde, caprui si caprui-verzui/hazel),
> cu o acuratete de aproximativ 63% pe setul de testare." (vezi tabelul de mai jos)
>
> Par: „...patru categorii — negru, saten, blond si grizonant — categoria roscat
> fiind eliminata deoarece nu se separa fiabil de saten doar din valorile HSV."

Asa textul devine 1:1 cu codul. (Daca preferi, pot ajusta codul sa elimine `hazel`
si sa ajunga efectiv la 3 categorii la ochi — dar atunci recalibram si reevaluam.)

### Cifre reale de evaluare (din known_issues.md + evaluate_pipeline.py)
| Atribut | Categorii in cod | Acuratete masurata |
|---|---|---|
| Ton ten | deschis / mediu / inchis (3) | **100%** (cu regula olive) |
| Subton | cald / rece / neutru / olive (4) | **40%** (sub-prod., doc.) |
| Culoare ochi | blue / green / brown / hazel (4) | **~63%** (12/19) |
| Culoare par | black / brunette / blonde / gray (4) | **~72%** (13/18) |
| Forma fata | EXPERIMENTAL, scos | ~35% < 60% baseline |

---

## 3.4.1 Extragere ton ten — CIELAB + ITA°

**Fragment A — citirea pielii, conversia CIELAB si formula ITA°.**
Sursa: [vision.py:170-179](vision.py#L170-L179)

```python
# MEDIANA pe canale = robusta la pixeli aberanti (umbre, fire de par, riduri)
median_bgr = np.median(pixeli, axis=0)
L, a, b = _bgr_la_lab_real(median_bgr)        # -> CIELAB real (L*:0-100)

# ITA = arctan((L* - 50) / b*) * 180/pi   (Chardon et al., 1991)
ita = float(np.degrees(np.arctan2(L - 50.0, b))) if b != 0 else 0.0

if _este_olive(ita, a, b):
    ton, subton = "mediu", "olive"            # ten luminos dar verde-galbui
else:
    ton, subton = _ton_3(ita), _subton(a, b)
```

**Fragment B — impartirea scarii ITA° in 3 categorii (pragurile calibrate).**
Sursa: [vision.py:76-91](vision.py#L76-L91)

```python
def _ton_3(ita):
    if ita > 41:  return "deschis"            # PRAGURILE 41 si 10 = punctul
    if ita > 10:  return "mediu"              # de calibrare empirica
    return "inchis"

def _este_olive(ita, a, b):
    # Tenul olive e luminos (ITA mare) dar cu subton verde-galbui:
    # rosu scazut (a* <= 4) + galben ridicat (b* >= 7). ITA singur l-ar clasifica
    # gresit ca "deschis"; regula asta il corecteaza la "mediu".
    return ita > 41 and a <= 4 and b >= 7 and b > a
```
> *Legenda:* „Clasificarea tonului pe scara ITA° in trei categorii; regula `_este_olive`
> separa nuantele olive, zona cea mai expusa la erori."
> **De ce:** A = baza teoretica citabila (ITA°); B = pragurile + corectia olive
> mentionate explicit in text. (Adaugarea regulii olive a urcat acuratetea de la
> ~85% la 100% pe set — vezi known_issues.md.)

**Fragment C (optional) — scriptul de calibrare a pragurilor.**
Sursa: [calibrare_ten.py](calibrare_ten.py) — afiseaza ITA + Lab pentru fiecare poza,
ca sa gasesti limita deschis/olive. Il poti mentiona ca unealta, fara cod, sau
pune 2-3 randuri din bucla de afisare.

---

## 3.4.2 Extragere subton — pastrat, dar nedeterminant

Sursa: [vision.py:94-103](vision.py#L94-L103)

```python
def _subton(a, b):
    """Estimare GROSIERA a subtonului din a* (rosu/verde) si b* (galben/albastru).
    ATENTIE: subtonul dintr-o poza necalibrata e nesigur - lumina il falsifica
    puternic. Orientativ, nu masuratoare exacta."""
    if b <= 0:
        return "rece"
    ratio = a / b
    if ratio > 0.5:   return "rece"
    if ratio < 0.25:  return "cald"
    return "neutru"
```
> *Legenda:* „Functia de estimare a subtonului, pastrata in cod, dar al carei
> rezultat nu este folosit ca filtru determinant (acuratete 40%, sensibila la lumina)."
> **De ce:** sustine direct argumentul metodologic din text (lipsa calibrarii
> hardware, comparatia cu Color IQ / spectrofotometru). Docstring-ul recunoaste
> singur limitarea — ideal de citat.

---

## 3.4.3 Extragere culoare ochi — iris + esantionare pe inel

**Fragment A — activarea reperelor de iris (refine_landmarks).**
Sursa: [vision.py:156-158](vision.py#L156-L158)

```python
with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                           refine_landmarks=True,        # adauga punctele de iris
                           min_detection_confidence=0.5) as fm:
```

**Fragment B — clasificarea in categorii din Hue/Saturation.**
Sursa: [vision.py:199-206](vision.py#L199-L206)

```python
def _categorie_ochi(h, s):
    if 95 <= h <= 130 and s > 30:           return "blue"
    if 35 <= h <= 90 and s > 30:            return "green"
    if (h <= 30 or h >= 160) and s > 20:    return "brown"
    if 10 <= s <= 40:                       return "hazel"   # caprui-verzui
    return "unknown"
```

**Fragment C — esantionarea DOAR pe inelul irisului (decizie metodologica).**
Sursa: [vision.py:233-244](vision.py#L233-L244) (trunchiat)

```python
# INEL (annulus): intre pupila (centru) si sclera/piele (margine). Irisul real e
# zona dintre raza 45% si 85% -> exclude pupila si inelul limbal (cauza confuziei
# ochi deschisi -> brown). Testat: bbox=60%, cerc-centru=47%, inel=63% (pastrat).
r_min = raza * 0.45
r_max = raza * 0.85
...
masca = inel & (V > 40) & (V < 230) & (S > 20)   # scoate pupila, reflexe, sclera
h_med = float(np.median(H[masca]))               # MEDIANA = robusta
```
> *Legenda:* „Esantionarea irisului pe un inel (45-85% din raza) pentru a exclude
> pupila si marginea limbala; varianta cu cea mai buna acuratete (63%) dintre cele
> trei testate."
> **De ce:** C documenteaza un trail metodologic real (bbox 60% / cerc 47% / inel
> 63%) — exact genul de decizie justificata care impresioneaza la evaluare.

---

## 3.4.4 Extragere culoare par — ROI extins deasupra fruntii

**Fragment A — extinderea regiunii de interes cu ~40% din inaltimea fetei.**
Sursa: [vision.py:333-338](vision.py#L333-L338)

```python
# Parul NU e in Face Mesh. Extindem un ROI deasupra fruntii, proportional cu
# inaltimea fetei (40% in sus), asumand ca acolo majoritatea pixelilor sunt par.
H_face = abs(y_barbie - y_top)
top = int(y_top - 0.4 * H_face)
bottom = int(y_top)
left = int(min(x_dr, x_st))
right = int(max(x_dr, x_st))
```

**Fragment B — clasificarea pe 4 categorii (discriminantul e VALUE, nu Hue).**
Sursa: [vision.py:304-316](vision.py#L304-L316)

```python
def _categorie_par(h, s, v):
    # Discriminantul principal e VALUE (luminozitatea): negru/saten/blond au
    # aceeasi nuanta calda (H~8-25), doar V ii separa (praguri 52 si 150).
    # 'red' (roscat) ELIMINAT: nu se separa de saten doar din HSV.
    if v < 52:    return "black"
    if s < 25:    return "gray"
    if v > 150:   return "blonde"
    return "brunette"
```
> *Legenda:* „Extinderea regiunii de interes deasupra fruntii (decizie metodologica
> impusa de limitele MediaPipe) si clasificarea pe luminozitate."
> **De ce:** A = decizia ta proprie (ROI extins) mentionata in text; B = arata
> onest ca sunt **4** categorii si ca `red` a fost eliminat (vezi corectura B de sus).

---

## 3.4.5 Tentativa forma fetei — rezultat negativ

Sursa: [vision.py:379-417](vision.py#L379-L417) (trunchiat — pastreaza docstring-ul!)

```python
def extract_face_shape(face_landmarks, image_shape):
    """Forma fetei din raporturi intre distante.
    ⚠️ EXPERIMENTAL - NU se foloseste in productie (nu e apelata de _analyze_img).
    REZULTAT NEGATIV: acuratete ~35% pe 20 poze, SUB baseline-ul majoritar (60%,
    predictie constanta 'oval'). Rapoartele geometrice se suprapun intre categorii."""
    ...
    length_to_width  = face_length / cheek_w      # 3 rapoarte geometrice
    forehead_to_jaw  = forehead_w / jaw_w
    cheekbone_to_jaw = cheek_w / jaw_w

    if length_to_width > 1.5:        cat = "oval"     # arbore de decizie simplu
    elif forehead_to_jaw > 1.3:      cat = "heart"
    elif cheekbone_to_jaw < 1.1 and length_to_width < 1.2:  cat = "square"
    else:                            cat = "round"
    return cat
```
> *Legenda:* „Functia experimentala de estimare a formei fetei: trei rapoarte
> geometrice + arbore de decizie. Pastrata in cod ca dovada a abordarii testate,
> dar exclusa din productie (35% < 60% baseline)."
> **De ce:** docstring-ul rezuma exact rezultatul negativ din text. Marcajul
> „NU se foloseste in productie" sustine decizia ta metodologica (nu integrezi
> artificial o componenta care nu bate baseline-ul).

---

## 3.5 Algoritmul de recomandare

**Fragment 3.5.1 — acelasi vocabular pentru profil si produs; potrivirea „1 vs N valori".**
Sursa: [recommender.py:65-71](recommender.py#L65-L71)

```python
def _se_potriveste(valoare_produs, valoare_user):
    if not valoare_user or valoare_user == 'oricare':
        return True
    optiuni = str(valoare_produs).lower().split('|')   # produsul poate avea N valori
    if 'toate' in optiuni:                              # 'toate' = universal
        return True
    return valoare_user.lower() in optiuni              # profilul are 1 valoare
```
> **De ce:** ilustreaza fix ideea din 3.5.1 — profilul are o singura valoare, produsul
> mai multe (separate prin `|`); potrivirea = valoarea profilului e in setul produsului.

**Fragment 3.5.2 — cele doua faze: filtre dure + scoring.**
Sursa: [recommender.py:131-164](recommender.py#L131-L164) (trunchiat)

```python
def recomanda(preferinte, df, numar=5):
    rezultate = df.copy()

    # FAZA 1 - FILTRE OBLIGATORII (nu admit compromis)
    if preferinte.get('categorie') not in (None, 'oricare'):
        rezultate = rezultate[rezultate['categorie'] == preferinte['categorie']]
    if preferinte.get('buget'):
        rezultate = rezultate[rezultate['pret'] <= float(preferinte['buget'])]
    if preferinte.get('doar_vegan'):
        rezultate = rezultate[rezultate['vegan'] == 'Da']
    if preferinte.get('doar_cruelty_free'):
        rezultate = rezultate[rezultate['cruelty_free'] == 'Da']

    # FAZA 2 - SCORING PONDERAT (fiecare criteriu potrivit adauga puncte)
    scoruri = [_scor(p, preferinte) for _, p in rezultate.iterrows()]
    rezultate = rezultate.assign(scor=[s for s, _ in scoruri])

    # FAZA 3 - sortare dupa scor, apoi RATING ca departajare (3.5.4)
    return rezultate.sort_values(['scor', 'rating'], ascending=[False, False]).head(numar)
```

**Fragment 3.5.3 — ponderile dupa importanta cosmetica (= Tabelul 3.1 in cod).**
Sursa: [recommender.py:25-52](recommender.py#L25-L52) (trunchiat)

```python
PONDERI = {
    'tip_ten': 3,            # DETERMINANT (criteriu de piele)
    'subton': 2,             # IMPORTANT
    'nuanta': 2,
    'acoperire': 2,
    'contrast': 1,           # COMPLEMENTAR (estetic)
    'ocazie': 1,
    'finish': 1,
    'suited_eye_color': 1,   # COMPLEMENTAR (din analiza foto, pondere mica)
    'suited_hair_color': 1,
}
PONDERE_INGREDIENT = 2       # cumulativ: fiecare ingredient potrivit adauga puncte
PONDERE_PROBLEMA = 2         # cumulativ: fiecare problema adresata adauga puncte
```

**Fragment 3.5.2/3.5.3 — calculul scorului (acumularea + contributiile cumulative).**
Sursa: [recommender.py:100-126](recommender.py#L100-L126) (trunchiat)

```python
def _scor(produs, preferinte):
    scor, motive = 0, []
    for camp, pondere in PONDERI.items():
        valoare_user = preferinte.get(camp)
        if valoare_user and valoare_user != 'oricare':
            if _se_potriveste(produs[camp], valoare_user):
                scor += pondere                       # criteriu potrivit -> + pondere
                motive.append(ETICHETE[camp])

    ingr = _ingrediente_potrivite(produs.get('ingrediente_cheie'),
                                  preferinte.get('ingrediente_cheie', []))
    if ingr:
        scor += PONDERE_INGREDIENT * len(ingr)        # cumulativ
    # ... idem pentru problemele pielii ...
    return scor, motive
```
> *Legenda (pune sub Tabelul 3.1):* „Ponderile reflecta ierarhia importantei
> cosmetice: criteriile de piele (tip ten = 3) cantaresc mai mult decat cele
> estetice (culoare ochi/par = 1)."
> **De ce:** PONDERI E literalmente Tabelul 3.1. `_scor` arata acumularea ponderata
> + contributiile cumulative (ingrediente/probleme) descrise in 3.5.2-3.5.3.

**Fragment 3.5.4 — inregistrarea fiecarei recomandari (pentru rapoarte + evaluare).**
Sursa: [recommender.py:180-192](recommender.py#L180-L192) (trunchiat)

```python
with get_db() as conn:
    cur = conn.execute(
        "INSERT INTO recommendations_log (preferinte_json, timp_executie_ms) VALUES (?, ?)",
        (json.dumps(pref_curate, ensure_ascii=False), elapsed_ms))
    log_id = cur.lastrowid
    for pozitie, (_, p) in enumerate(rezultate.iterrows(), start=1):
        conn.execute("INSERT INTO recommendation_products "
                     "(log_id, produs_id, pozitie, scor) VALUES (?, ?, ?, ?)",
                     (log_id, int(p['id']), pozitie, int(p['scor'])))
```
> **De ce:** sustine fraza „fiecare recomandare ... este inregistrata in baza de
> date, ceea ce permite reconstituirea rapoartelor si evaluarea ulterioara".

---

## 3.6 Layer agentic AI (n8n)

**Fragment 3.6.1 — payload-ul trimis catre webhook (profil + produse).**
Sursa: [app.py:252-278](app.py#L252-L278) (trunchiat)

```python
def _construieste_payload(email, preferinte, produse, log_id):
    return {
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'log_id': log_id,
        'email': email,
        'preferinte': pref_curate,                 # profilul utilizatorului
        'produse_recomandate': [                   # lista de produse
            {'id': int(p['id']), 'nume': p['nume'], 'brand': p['brand'],
             'categorie': p['categorie'], 'pret': float(p['pret']),
             'rating': float(p['rating']), 'descriere': p['descriere']}
            for p in produse
        ],
    }
```

**Fragment 3.6.3 — apel asincron + protectie prin proiectare + robustete.**
Sursa: [webhook_dispatcher.py:79-104](webhook_dispatcher.py#L79-L104) (trunchiat)

```python
def trimite_webhook(payload, email='', log_id=None):
    url = config.N8N_WEBHOOK_URL
    if not url:                                    # ROBUSTETE: neconfigurat -> 'skipped'
        _logheaza(log_id, email, '', payload, status='skipped', ...)
        return 'skipped'                           # utilizatorul tot primeste recomandarile

    # ASINCRON: fir separat, ca trimiterea email-ului sa nu intarzie raspunsul HTTP.
    thread = threading.Thread(target=_executa_post,
                              args=(log_id, email, payload, url, timeout), daemon=True)
    thread.start()
    return 'dispatched'
```
Si conditionarea pe email (protectia datelor prin proiectare), din [app.py:213-218](app.py#L213-L218):
```python
status_webhook = None
if email:                                          # canal extern DOAR la consimtamant
    payload = _construieste_payload(email, preferinte, produse, log_id)
    status_webhook = webhook_dispatcher.trimite_webhook(payload, email=email, log_id=log_id)
```
> *Legenda:* „Integrarea asincrona cu n8n: firul separat nu intarzie raspunsul,
> apelul se face doar daca exista email, iar fiecare incercare e logata (success /
> error / skipped)."
> **De ce:** acopera toate cele trei idei din 3.6.3 — asincronie, protectia datelor
> (gated pe email), robustete (skipped + logare).

---

## 3.7 Evaluare experimentala

**Fragment 3.7.1 — ground truth pentru analiza foto (etichete reale, vizuale).**
Sursa: [evaluate_pipeline.py:26-47](evaluate_pipeline.py#L26-L47) (extras)

```python
# ton: valoare unica.  subton/ochi: SET de valori acceptabile (eticheta vizuala
# e adesea compusa: "cald-neutru", "albastri-gri").
ETICHETE = {
    11: {"ton": "deschis", "subton": {"rece"},          "ochi": {"blue"},  "par": "blonde"},
    21: {"ton": "mediu",   "subton": {"cald", "olive"},  "ochi": {"brown"}, "par": "black"},
    # ... 20 de poze (3-22) ...
}
```

**Fragment 3.7.1 — schema de potrivire + matricea de confuzie pe ton.**
Sursa: [evaluate_pipeline.py:72-76, 118-122](evaluate_pipeline.py#L72-L122) (trunchiat)

```python
# TON: potrivire EXACTA.  SUBTON/OCHI: corect daca nimereste UNA din valorile acceptabile.
ton_corect = r["ton"] == real["ton"]
subton_corect = r["subton"] in real["subton"]
confuzie[real["ton"]][r["ton"]] += 1            # matrice de confuzie: real x prezis
```

**Fragment 3.7.2 — cei doi algoritmi comparati (rule-based vs random cu seed fix).**
Sursa: [eval_h1.py:44-56](eval_h1.py#L44-L56)

```python
def rule_based_top5(df, p):
    """Top 5 de la algoritmul rule-based ponderat."""
    rez, _ = recomanda(preferinte(p), df, numar=5, log=False)
    return list(rez['id'])

def random_top5(df, p):
    """Baseline: 5 produse aleatoare, SEED FIX pe profil (reproducibil).
    Aplica aceleasi filtre dure ca rule-based."""
    random.seed(42 + p['id'])
    pool = df[df['tip_produs'] == 'makeup']
    return random.sample(list(pool['id']), min(5, len(pool)))
```

**Fragment 3.7.2 — precision@5.**
Sursa: [eval_precision_at_5.py:40-44](eval_precision_at_5.py#L40-L44)

```python
def precision_at_5(top5, profile_id, rel):
    if not top5:
        return 0.0
    relevante = sum(1 for pid in top5 if rel.get((profile_id, pid), False))
    return relevante / len(top5)              # produse relevante in top 5 / 5
```
> *Legenda:* „Precision@5: proportia produselor relevante din primele cinci propuse.
> Reperul aleator foloseste o samanta fixa pentru reproducibilitate si aceleasi
> filtre dure ca motorul rule-based."
> **De ce:** cele trei fragmente acopera exact 3.7 — ground truth + schema de
> potrivire (matrice confuzie), cei doi algoritmi, si metrica precision@5.
> Etichetarea oarba (pooling) se vede in `genereaza_template_h1.py`, daca vrei sa
> o citezi si pe ea.

---

## 3.8 Limitari tehnice si etice

Aceasta sectiune e in mare parte argumentativa — codul de sustinere a fost deja
extras mai sus. Trimiteri utile:
- **Sensibilitate la iluminare** -> docstring `_subton` (3.4.2) + corectia
  gray-world `_white_balance_grayworld` ([vision.py:109-118](vision.py#L109-L118)).
- **Forma fetei** -> `extract_face_shape` (3.4.5).
- **Catalog / bias pe ten** -> `validate_catalog.py` (verifica distributia pe ton)
  + metrica ITA° validata pe toata gama (3.4.1).
- **Protectia datelor prin proiectare:**
  - poza doar in memorie -> [app.py:99](app.py#L99) (vezi FRAGMENTE_COD_FRONTEND §6);
  - doar hash in jurnal -> `logheaza_extractie` ([db.py:117-129](db.py#L117-L129),
    FRAGMENTE_COD_FRONTEND §5);
  - email doar la initiativa utilizatorului -> [app.py:213-218](app.py#L213-L218) (3.6.3 de mai sus).

---

## Recomandare de selectie (daca spatiul e limitat)

| Sectiune | Fragment esential | De ce |
|---|---|---|
| 3.4.1 ton | ITA° + `_ton_3`/`_este_olive` | baza stiintifica citabila |
| 3.4.3 ochi | `_categorie_ochi` + inel (annulus) | trail metodologic + categoriile reale |
| 3.4.5 forma | docstring `extract_face_shape` | rezultatul negativ |
| 3.5 | `recomanda` (3 faze) + `PONDERI` | inima lucrarii |
| 3.6 | `trimite_webhook` + gating pe email | asincronie + protectia datelor |
| 3.7 | `precision_at_5` + `rule_based/random_top5` | metrica + baseline |

**Inainte de orice:** rezolva cele doua corecturi din capul fisierului (ochi: 4
categorii / 63%; par: 4 categorii, `red` eliminat). Sunt cele mai usor de
„prins" la o citire atenta a codului.
