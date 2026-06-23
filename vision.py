# -*- coding: utf-8 -*-
"""
vision.py — extragere ton ten din poza, cu ITA° (Individual Typology Angle)

CE FACE
    Primeste o poza (cale pe disc SAU bytes din upload), detecteaza fata cu
    MediaPipe, citeste culoarea pielii de pe obraji + frunte, o transforma in
    CIELAB, calculeaza ITA° si clasifica tenul in: deschis / mediu / inchis.

DE CE ITA°
    Este metrica standard din dermatologie (Chardon et al., 1991) pentru
    clasificarea OBIECTIVA a tonului pielii -> o poti CITA in lucrare, spre
    deosebire de "am intrebat un model AI". Formula:
        ITA = arctan( (L* - 50) / b* ) * 180/pi
    L* = luminozitate (0=negru, 100=alb), b* = axa galben(+)/albastru(-).

DEPENDINTE
    pip install opencv-python mediapipe numpy

NOTA
    Folosim API-ul "solutions" din MediaPipe (mp.solutions.face_mesh) pentru ca
    e simplu si bine documentat. Exista si API-ul nou "Tasks" (FaceLandmarker) —
    verifica documentatia curenta daca vrei sa migrezi.
"""

import cv2
import numpy as np
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh

# Puncte de pe piele "curata" (evitam ochi, sprancene, buze): obraji + frunte.
# Indici din Face Mesh (model cu 468 de puncte).
SKIN_LANDMARKS = [
    50, 101, 118, 205, 207,     # obraz stang
    280, 330, 347, 425, 427,    # obraz drept
    151, 9, 107, 336, 10,       # frunte
]

# Landmarks iris (DOAR daca refine_landmarks=True; altfel nu exista).
# 1 centru + 4 margini per ochi.
IRIS_DREPT = [468, 469, 470, 471, 472]
IRIS_STANG = [473, 474, 475, 476, 477]

# Landmarks pentru pozitionarea zonei de PAR (parul NU e in Face Mesh - folosim
# limita de sus a fruntii ca reper si extindem ROI deasupra ei).
PAR_TOP_FRUNTE = 10    # centrul de sus al fruntii
PAR_COLT_DR = 67       # coltul dreapta-sus al fetei
PAR_COLT_ST = 297      # coltul stanga-sus al fetei
PAR_BARBIE = 152       # barbie (pt inaltimea fetei)

# Landmarks pentru FORMA FETEI (geometrie, nu culoare - invariant la lumina).
FATA_TOP = 10          # top frunte (lungime)
FATA_BARBIE = 152      # barbie (lungime)
FRUNTE_ST = 54         # frunte stanga (latime frunte)
FRUNTE_DR = 284        # frunte dreapta
OBRAZ_ST = 234         # obraz stang (latime obraji - cel mai lat)
OBRAZ_DR = 454         # obraz drept
FALCA_ST = 172         # falca stanga (latime falca)
FALCA_DR = 397         # falca dreapta


# ---------------------------------------------------------------------------
# Clasificare
# ---------------------------------------------------------------------------
def _eticheta_ita(ita):
    """Scala Chardon cu 6 clase — eticheta detaliata, citabila in lucrare."""
    if ita > 55:  return "very light"
    if ita > 41:  return "light"
    if ita > 28:  return "intermediate"
    if ita > 10:  return "tan"
    if ita > -30: return "brown"
    return "dark"


def _ton_3(ita):
    """Mapare la cele 3 valori din aplicatia ta.
    PRAGURILE (41 si 10) sunt punctul tau de CALIBRARE — le ajustezi pe
    pozele tale ca sa maximizezi acuratetea (vezi evaluate_folder)."""
    if ita > 41:  return "deschis"
    if ita > 10:  return "mediu"
    return "inchis"


def _este_olive(ita, a, b):
    """Tenul OLIVE (mediteraneean) e luminos (ITA mare -> ar parea 'deschis'),
    dar are subton verde-galbui: ROSU SCAZUT (a* mic) si GALBEN RIDICAT (b*).
    ITA° masoara doar luminozitatea, deci nu il distinge - de aici regula asta
    suplimentara pe a*/b*. Pragurile (a*<=4, b*>=7) sunt calibrate pe setul de
    poze de test; pe alt set pot necesita reajustare."""
    return ita > 41 and a <= 4 and b >= 7 and b > a


def _subton(a, b):
    """Estimare GROSIERA a subtonului din a* (rosu/verde) si b* (galben/albastru).
    ATENTIE: subtonul dintr-o poza necalibrata e nesigur (lumina il falsifica
    puternic). Trateaza-l ca orientativ si mentioneaza limitarea in lucrare."""
    if b <= 0:
        return "rece"
    ratio = a / b
    if ratio > 0.5:   return "rece"     # domina rosul -> roz/rece
    if ratio < 0.25:  return "cald"     # domina galbenul -> cald
    return "neutru"


# ---------------------------------------------------------------------------
# Procesare imagine
# ---------------------------------------------------------------------------
def _white_balance_grayworld(img):
    """Corectie simpla de lumina (gray-world). Ajuta cand poza are o dominanta
    de culoare (ex. bec galben). Nu rezolva tot, dar reduce erorile de subton."""
    result = img.astype(np.float32)
    avg = result.reshape(-1, 3).mean(axis=0)   # medii pe B, G, R
    gray = avg.mean()
    for c in range(3):
        if avg[c] > 0:
            result[:, :, c] *= gray / avg[c]
    return np.clip(result, 0, 255).astype(np.uint8)


def _colecteaza_pixeli_piele(img, landmarks, w, h, win=6):
    """Aduna pixeli din ferestre mici (2*win) in jurul fiecarui punct de piele."""
    pixeli = []
    for idx in SKIN_LANDMARKS:
        lm = landmarks[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        patch = img[max(0, y - win):y + win, max(0, x - win):x + win]
        if patch.size:
            pixeli.append(patch.reshape(-1, 3))
    return np.vstack(pixeli) if pixeli else None


def _bgr_la_lab_real(bgr_pixel):
    """OpenCV scaleaza Lab pt imagini 8-bit (L:0-255, a/b:0-255 cu offset +128).
    Convertim la CIELAB REAL: L*:0-100, a*/b*: ~ -128..127.
    Pasul asta e ESENTIAL — fara el, ITA° iese complet gresit."""
    px = np.uint8([[bgr_pixel]])
    L, a, b = cv2.cvtColor(px, cv2.COLOR_BGR2LAB)[0][0].astype(np.float32)
    L = L * 100.0 / 255.0
    a = a - 128.0
    b = b - 128.0
    return L, a, b


def _analyze_img(img, white_balance=True):
    """Nucleul: primeste o imagine OpenCV (BGR) si returneaza profilul."""
    if img is None:
        return {"ok": False, "error": "Imagine invalida."}
    # Pastram poza ORIGINALA pentru culoarea ochilor (white-balance-ul ajuta la
    # ton/subton, dar deformeaza nuanta iris-ului).
    img_original = img
    if white_balance:
        img = _white_balance_grayworld(img)

    h, w = img.shape[:2]
    with mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1,
                               refine_landmarks=True,
                               min_detection_confidence=0.5) as fm:
        res = fm.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if not res.multi_face_landmarks:
        return {"ok": False, "error": "Nu am detectat nicio fata."}

    lms = res.multi_face_landmarks[0].landmark
    pixeli = _colecteaza_pixeli_piele(img, lms, w, h)
    if pixeli is None or len(pixeli) < 50:
        return {"ok": False, "error": "Nu pot citi suficienta piele."}

    # MEDIANA pe canale = robusta la pixeli aberanti (umbre, fire de par, riduri)
    median_bgr = np.median(pixeli, axis=0)
    L, a, b = _bgr_la_lab_real(median_bgr)

    ita = float(np.degrees(np.arctan2(L - 50.0, b))) if b != 0 else 0.0

    # Regula olive: ten luminos dar cu subton verde-galbui -> mediu, nu deschis.
    if _este_olive(ita, a, b):
        ton, subton = "mediu", "olive"
    else:
        ton, subton = _ton_3(ita), _subton(a, b)

    return {
        "ok": True,
        "ton": ton,                         # pt aplicatie: deschis/mediu/inchis
        "ton_detaliat": _eticheta_ita(ita), # scala Chardon (citabila)
        "subton": subton,                   # GROSIER — vezi limitari
        "culoare_ochi": extract_eye_color(img_original, lms),  # blue/green/brown/hazel/unknown
        "culoare_par": extract_hair_color(img_original, lms),  # black/brunette/blonde/red/gray/unknown
        # forma_fata: EXCLUSA din productie (rezultat negativ - vezi extract_face_shape)
        "ITA": round(ita, 1),
        "Lab": [round(L, 1), round(a, 1), round(b, 1)],  # util la calibrare
    }


# ---------------------------------------------------------------------------
# Culoarea ochilor (iris) — mai grea decat tonul: iris mic, neuniform, plin de
# pixeli "outlier" (pupila, reflexe, gene, sclera). Strategia: bounding box pe
# landmarks iris -> filtrare pixeli -> nuanta dominanta -> mapare pe categorii.
# ---------------------------------------------------------------------------
def _categorie_ochi(h, s):
    """Mapeaza Hue (0-179 in OpenCV) si Saturation pe 4 categorii.
    PRAGURILE sunt orientative — calibreaza-le pe pozele tale de test."""
    if 95 <= h <= 130 and s > 30:           return "blue"
    if 35 <= h <= 90 and s > 30:            return "green"
    if (h <= 30 or h >= 160) and s > 20:    return "brown"
    if 10 <= s <= 40:                       return "hazel"   # mix, indeterminat
    return "unknown"


def _centru_raza_iris(landmarks, indici, w, h):
    """Centrul iris-ului (landmark 468/473) si raza (mediana distantelor catre
    cele 4 margini). Lucram cu un CERC, nu cu un dreptunghi, ca sa nu prindem
    colturile cu sclera/piele."""
    cx = landmarks[indici[0]].x * w
    cy = landmarks[indici[0]].y * h
    raze = []
    for i in indici[1:]:
        dx = landmarks[i].x * w - cx
        dy = landmarks[i].y * h - cy
        raze.append((dx * dx + dy * dy) ** 0.5)
    raza = float(np.median(raze)) if raze else 0.0
    return cx, cy, raza


def _culoare_un_ochi(img, cx, cy, raza):
    """Returneaza (categorie, saturatie, hue) pentru un ochi, sau (None, 0, 0).
    Esantioneaza DOAR miezul iris-ului (cerc cu raza 70%) ca sa evite inelul
    limbal si pielea din jur - cauza principala a confuziei ochi deschisi->brown."""
    if raza < 4:                 # iris prea mic (capcana 3)
        return None, 0.0, 0.0

    h_img, w_img = img.shape[:2]
    # INEL (annulus): intre pupila (centru) si piele/sclera (margine). Irisul
    # propriu-zis e zona dintre raza 45% si 85% - exclude pupila si inelul limbal.
    r_min = raza * 0.45
    r_max = raza * 0.85
    x0 = max(0, int(cx - r_max)); x1 = min(w_img, int(cx + r_max) + 1)
    y0 = max(0, int(cy - r_max)); y1 = min(h_img, int(cy + r_max) + 1)
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return None, 0.0, 0.0

    yy, xx = np.ogrid[y0:y1, x0:x1]
    dist2 = (xx - cx) ** 2 + (yy - cy) ** 2
    inel = (dist2 >= r_min ** 2) & (dist2 <= r_max ** 2)

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0].astype(np.float32)
    S = hsv[:, :, 1].astype(np.float32)
    V = hsv[:, :, 2].astype(np.float32)

    if V[inel].size == 0 or V[inel].mean() < 30:   # capcana 5: ochi inchis/intunecat
        return None, 0.0, 0.0

    # Filtre: scoate pupila/genele (V mic), reflexele/sclera (V mare sau S mic).
    masca = inel & (V > 40) & (V < 230) & (S > 20)
    if int(masca.sum()) < 10:    # prea putini pixeli de iris ramasi
        return None, 0.0, 0.0

    # MEDIANA = mai robusta decat media la marginea gri-verzuie a iris-ului.
    h_med = float(np.median(H[masca]))
    s_med = float(np.median(S[masca]))
    return _categorie_ochi(h_med, s_med), s_med, h_med


def extract_eye_color(image, face_landmarks):
    """Extrage culoarea dominanta a ochilor.

    Args:
        image: ndarray BGR cu fata vizibila.
        face_landmarks: lista de landmarks MediaPipe (refine_landmarks=True).

    Returns:
        una din "blue" / "green" / "brown" / "hazel", sau "unknown".
    """
    if len(face_landmarks) < 478:    # capcana 1: refine_landmarks dezactivat
        return "unknown"

    h, w = image.shape[:2]
    rezultate = []
    for indici in (IRIS_DREPT, IRIS_STANG):
        cx, cy, raza = _centru_raza_iris(face_landmarks, indici, w, h)
        cat, sat, _hue = _culoare_un_ochi(image, cx, cy, raza)
        if cat and cat != "unknown":
            rezultate.append((cat, sat))

    if not rezultate:
        return "unknown"
    if len(rezultate) == 1:
        return rezultate[0][0]

    # Agregare pe 2 ochi: daca difera, alegem ochiul cu saturatie mai mare
    # (culoare mai "decisa", mai putin afectata de umbra/reflexe).
    (c1, s1), (c2, s2) = rezultate
    if c1 == c2:
        return c1
    return c1 if s1 >= s2 else c2


# ---------------------------------------------------------------------------
# Culoarea parului — diferit de ten/ochi: parul NU e in Face Mesh. Strategie:
# extindem un ROI deasupra fruntii (proportional cu inaltimea fetei), asumand
# ca majoritatea pixelilor de acolo sunt par. Apoi filtre HSV + mediana.
# ---------------------------------------------------------------------------
def _categorie_par(h, s, v):
    """Mapeaza H/S/V medii pe 4 categorii (black/brunette/blonde/gray).

    Discriminantul principal e VALUE (luminozitatea): parul negru/saten/blond au
    toate aceeasi nuanta calda (H ~8-25), deci Hue nu ajuta - doar V ii separa.
    Pragurile (52 si 150) sunt calibrate pe setul de test.

    'red' (roscat/aramiu) a fost ELIMINAT: nu se separa de saten doar din HSV
    (aceeasi nuanta). Vezi known_issues.md."""
    if v < 52:    return "black"      # foarte inchis
    if s < 25:    return "gray"       # foarte putina culoare (par carunt)
    if v > 150:   return "blonde"     # luminos
    return "brunette"                 # mediu (include si roscatul)


def extract_hair_color(image, face_landmarks, image_shape=None):
    """Extrage culoarea dominanta a parului din zona de deasupra fruntii.

    Returns: "black"/"brunette"/"blonde"/"red"/"gray" sau "unknown".
    """
    h_img, w_img = (image_shape[:2] if image_shape is not None else image.shape[:2])
    try:
        y_top = face_landmarks[PAR_TOP_FRUNTE].y * h_img
        y_barbie = face_landmarks[PAR_BARBIE].y * h_img
        x_dr = face_landmarks[PAR_COLT_DR].x * w_img
        x_st = face_landmarks[PAR_COLT_ST].x * w_img
    except (IndexError, AttributeError):
        return "unknown"

    # Inaltimea fetei -> extindem ROI in sus cu 40% din ea.
    H_face = abs(y_barbie - y_top)
    top = int(y_top - 0.4 * H_face)
    bottom = int(y_top)
    left = int(min(x_dr, x_st))
    right = int(max(x_dr, x_st))

    if top < 0:                  # capcana 4: poza taiata sus -> nu vedem parul
        return "unknown"
    top, bottom = max(0, top), min(h_img, bottom)
    left, right = max(0, left), min(w_img, right)
    if bottom - top < 5 or right - left < 5:
        return "unknown"

    roi = image[top:bottom, left:right]
    if roi.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    H = hsv[:, :, 0].astype(np.float32)
    S = hsv[:, :, 1].astype(np.float32)
    V = hsv[:, :, 2].astype(np.float32)

    # Filtre: scoate highlights/lumina (V>240) si benzi colorate artificiale (S>200).
    masca = (V <= 240) & (S <= 200)
    if int(masca.sum()) < 20:
        return "unknown"

    h_med = float(np.median(H[masca]))
    s_med = float(np.median(S[masca]))
    v_med = float(np.median(V[masca]))
    return _categorie_par(h_med, s_med, v_med)


# ---------------------------------------------------------------------------
# Forma fetei — singurul atribut GEOMETRIC: nu lucram cu pixeli/culoare, ci cu
# RAPOARTE intre distante euclidiene ale landmarks. Avantaj: invariant la lumina
# si la scara (raportul e la fel pe orice rezolutie).
# ---------------------------------------------------------------------------
def _dist(landmarks, i, j, w, h):
    """Distanta euclidiana in pixeli intre 2 landmarks (coord. normalizate->px)."""
    x1, y1 = landmarks[i].x * w, landmarks[i].y * h
    x2, y2 = landmarks[j].x * w, landmarks[j].y * h
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def extract_face_shape(face_landmarks, image_shape):
    """Forma fetei din raporturi intre distante. NU primeste imaginea.
    Returns: oval/round/square/heart sau unknown.

    ⚠️ EXPERIMENTAL — NU se foloseste in productie (nu e apelata de
    _analyze_img). REZULTAT NEGATIV documentat: acuratete ~35% pe setul de 20
    poze, SUB baseline-ul majoritar (60%, predictie constanta "oval").
    Rapoartele geometrice se suprapun complet intre categorii - landmark-urile
    pe pielea fetei nu capteaza conturul osos / angularitatea falcii.
    Vezi known_issues.md si capitolele 3.4.4 / 3.7 / 4.4 ale lucrarii.
    Pastrata ca dovada a abordarii testate (CNN dedicat = directie viitoare)."""
    h_img, w_img = image_shape[:2]
    try:
        face_length = _dist(face_landmarks, FATA_TOP, FATA_BARBIE, w_img, h_img)
        forehead_w = _dist(face_landmarks, FRUNTE_ST, FRUNTE_DR, w_img, h_img)
        cheek_w = _dist(face_landmarks, OBRAZ_ST, OBRAZ_DR, w_img, h_img)
        jaw_w = _dist(face_landmarks, FALCA_ST, FALCA_DR, w_img, h_img)
    except (IndexError, AttributeError):
        return "unknown"

    if cheek_w == 0 or jaw_w == 0:
        return "unknown"

    # 3 rapoarte cheie (invariante la scara).
    length_to_width = face_length / cheek_w
    forehead_to_jaw = forehead_w / jaw_w
    cheekbone_to_jaw = cheek_w / jaw_w

    # Arbore de decizie (praguri orientative - de calibrat pe set).
    if length_to_width > 1.5:
        cat = "oval"                                          # fata alungita
    elif forehead_to_jaw > 1.3:
        cat = "heart"                                         # frunte >> falca
    elif cheekbone_to_jaw < 1.1 and length_to_width < 1.2:
        cat = "square"                                        # falca lata, ne-alungita
    else:
        cat = "round"

    return cat


# ---------------------------------------------------------------------------
# API public
# ---------------------------------------------------------------------------
def extract_profile(image_path, white_balance=True):
    """Din cale pe disc."""
    return _analyze_img(cv2.imread(image_path), white_balance)


def extract_profile_from_bytes(image_bytes, white_balance=True):
    """Din bytes (upload Flask) — NU scrie poza pe disc, deci respecti
    promisiunea 'Poza nu este pastrata dupa analiza'."""
    arr = np.frombuffer(image_bytes, np.uint8)
    return _analyze_img(cv2.imdecode(arr, cv2.IMREAD_COLOR), white_balance)


# ---------------------------------------------------------------------------
# Masurarea acuratetei — pentru capitolul de rezultate al lucrarii
# ---------------------------------------------------------------------------
def evaluate_folder(root):
    """Pune poze etichetate manual in:
        root/deschis/ , root/mediu/ , root/inchis/
    Functia ruleaza extractia pe fiecare si compara cu eticheta (numele
    folderului). Returneaza acuratetea — exact cifra pe care o aperi la sustinere
    si o pui in tabelul de rezultate. Ruleaza-o dupa ce ajustezi pragurile."""
    import os
    total = corecte = 0
    per_clasa = {}
    for label in ("deschis", "mediu", "inchis"):
        d = os.path.join(root, label)
        if not os.path.isdir(d):
            continue
        tc = cc = 0
        for fn in os.listdir(d):
            r = extract_profile(os.path.join(d, fn))
            if not r.get("ok"):
                continue
            tc += 1
            cc += (r["ton"] == label)
        per_clasa[label] = {"n": tc, "corecte": cc}
        total += tc
        corecte += cc
    return {
        "n_total": total,
        "acuratete": round(corecte / total, 3) if total else None,
        "per_clasa": per_clasa,
    }


if __name__ == "__main__":
    import sys, json
    cale = sys.argv[1] if len(sys.argv) > 1 else "test.jpg"
    print(json.dumps(extract_profile(cale), ensure_ascii=False, indent=2))
