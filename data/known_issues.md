# Limitari cunoscute (known issues)

Document cu limitarile cunoscute ale modulului de analiza foto (`vision.py`).
Le documentam onest — sunt limitari intrinseci ale abordarii, nu bug-uri de
rezolvat. Mentionarea lor in lucrare arata intelegerea problemei.

## Analiza tonului pielii (ITA°)

- **Solid si citabil.** Clasificarea tonului foloseste metrica ITA° (Individual
  Typology Angle, Chardon et al., 1991), standard in dermatologie.
- **Pragurile 41 si 10** (`_ton_3`) sunt punctul de calibrare. Au fost ajustate
  pe setul de poze de test; pe populatii diferite pot necesita recalibrare.
- **Lumina influenteaza luminozitatea (L\*).** O poza supraexpusa poate ridica
  artificial ITA° (ten clasificat mai deschis decat este). Corectia gray-world
  reduce, dar nu elimina, acest efect.
- **Tenul olive** este luminos (ITA° mare), deci ITA° singur il clasifica gresit
  ca "deschis". Adaugat o regula suplimentara (`_este_olive`): roso scazut
  (a\* <= 4) + galben ridicat (b\* >= 7) -> "mediu" cu subton "olive". A crescut
  acuratetea tonului de la ~85% la 100% pe setul de test (22 poze). PRAGURILE
  a\*/b\* sunt calibrate pe acest set si pot necesita reajustare pe alt set.

## Subtonul (cald / rece / neutru / olive)

- **Estimare grosiera, nesigura.** Subtonul e dedus din a\* / b\* (CIELAB) si
  este **puternic influentat de lumina** din poza. La lumina artificiala
  (bec galben/alb) rezultatul poate fi gresit.
- **Acuratete masurata: 40% (8/20)** pe setul de test (`evaluate_pipeline.py`).
  Tendinta spre "rece" la poze cald/neutru. Subtonul "olive" e detectat corect
  (vine din regula olive de la ton).
- Trebuie tratat ca **orientativ**, nu ca o masuratoare exacta. Este o limitare
  cunoscuta si acceptata a abordarii dintr-o singura poza necalibrata.

## Culoarea ochilor (blue / green / brown / hazel)

- **Mai grea decat tonul.** Iris-ul e mic (~50x50 px pe o poza tipica),
  neuniform (pete, inele, gradiente) si plin de pixeli care nu fac parte din el
  (pupila, reflexe, gene, sclera).
- **Pragurile Hue/Saturation sunt orientative** si trebuie calibrate pe poze de
  test. Ochii **caprui** sunt cei mai problematici: nuanta lor e aproape de
  granita cu verdele, iar media/mediana poate aluneca spre "green".
- **Lentile de contact colorate:** imposibil de detectat doar din culoare —
  analiza va raporta culoarea lentilei, nu a iris-ului real.
- **Poze mici (< 500x500 px):** iris-ul ajunge ~15x15 px, prea putin pentru o
  estimare statistica solida -> se returneaza "unknown".
- **Ochi inchisi / pe jumatate:** iris partial vizibil sau regiune intunecata
  (V mediu < 30) -> "unknown".
- **Heterocromie** (ochi de culori diferite): rara, dar agregarea pe 2 ochi
  alege ochiul cu saturatia mai mare, deci poate masca diferenta.
- **Acuratete masurata: ~63% (12/19)** pe setul de test (`evaluate_pipeline.py`).
  Ochii **caprui ies corect**, dar exista o **tendinta spre "brown"**:
  ochii albastri/verzi/gri sunt uneori cititi "brown". Categoria "gri" nu exista.
- **Trail metodologic** (esantionarea regiunii irisului): testate 3 variante pe
  acelasi set — dreptunghi/bbox = 60%, cerc pe centru = 47% (prinde pupila si
  reflexele), **inel/annulus (raza 45-85%) = 63%, varianta pastrata** (cea mai
  corecta: exclude pupila si inelul limbal). Peste ~63% nu se mai poate fara
  overfitting pe cele 20 de poze - limita intrinseca a abordarii dintr-o poza.

## Culoarea parului (black / brunette / blonde / gray)

- **Diferit metodologic de ten/ochi:** parul NU e in Face Mesh. Se foloseste un
  ROI extins deasupra fruntii (landmarks 10, 67, 152, 297), proportional cu
  inaltimea fetei (40% in sus), apoi filtre HSV + mediana pe H/S/V.
- **Discriminantul principal e VALUE (luminozitatea)**, nu Hue: negru/saten/blond
  au aceeasi nuanta calda; doar luminozitatea ii separa (praguri V: 52 si 150,
  calibrate pe set).
- **'red' (roscat/aramiu) ELIMINAT** ca si categorie: nu se separa de saten doar
  din HSV (aceeasi nuanta). In setul de test exista 1 singura poza roscata, la
  care ROI-ul a esuat. Contopit cu brunette. (Alternativa pentru viitor: model
  dedicat / spatiu de culoare diferit.)
- **Acuratete masurata: ~72% (13/18)** pe setul de test (`evaluate_pipeline.py`),
  exclus 'unknown'. Erori tipice: blond inchis vs saten (granita pe V), si ROI
  care prinde frunte/fundal cand parul e strans/breton ridicat.
- **Capcane** (documentate, nerezolvate de abordarea simpla): chelie/par foarte
  scurt (ROI prinde piele), palarie / fundal de culoare similara, par strans la
  spate (frunte expusa). La testare se exclud pozele cu palarii.
- **Alternativa neimplementata:** model dedicat de segmentare par (ex. MediaPipe
  Selfie Segmentation / U-Net) - mai precis, dar mai complex. Compromis
  complexitate vs precizie, in scopul standard al lucrarii.

## Sprint 4 - Rezultat negativ: extragere forma fetei

### Abordare testata
Clasificare in 4 categorii (oval/round/square/heart) pe baza raporturilor intre
landmarks faciale MediaPipe (3 rapoarte: length/width, forehead/jaw,
cheekbone/jaw) si un arbore de decizie. Functia `extract_face_shape` exista in
`vision.py` dar e marcata EXPERIMENTAL si NU e apelata de `_analyze_img`.

### Rezultate
- Acuratete arbore de decizie: ~35% (set 20 poze etichetate manual).
- Baseline majoritar (predictie constanta "oval"): 60%.
- Algoritmul nu bate baseline-ul → fara semnal util.

### Diagnoza
- Rapoartele se SUPRAPUN complet intre categorii (ex. L/W: oval 1.15-1.30,
  round 1.18-1.25 - aceeasi plaja).
- Variabilitate intra-clasa > variabilitate inter-clasa.
- Landmark-urile sunt pe suprafata pielii, nu pe os → conturul facial si
  angularitatea falcii (ce diferentiaza vizual formele) nu sunt captate.
- Spatiu de feature insuficient (3 dimensiuni liniare).

### Decizie
- Eliminata din pipeline-ul de productie.
- Functie pastrata ca EXPERIMENTAL in cod (dovada abordarii testate).
- Documentare in capitolele 3.4.4 + 3.7 + 4.4 ale lucrarii.

### Reformulare ipoteza (H3)
H3 devine: "Abordarile bazate pe raporturi geometrice simple intre landmarks NU
produc o clasificare fiabila a formei fetei comparativ cu baseline-ul majoritar."
Prag: acuratete rapoarte < acuratete baseline → ipoteza CONFIRMATA (un rezultat
negativ confirmat e academic mai puternic decat eliminarea ipotezei).

### Directii viitoare
- Model CNN dedicat (face shape classification, ex. Hsu et al. 2017).
- PCA pe toate cele 468 landmarks.
- Combinare cu poza de profil (informatie laterala).

## Integrarea culorii ochilor / parului in recomandari (suited_*)

- Coloanele `suited_eye_color` / `suited_hair_color` din tabela products sunt
  etichetate AUTOMAT (`eticheteaza_culori.py`), prin reguli de teoria culorilor
  pe baza categoriei + subtonului produsului - NU avem nuanta exacta a fiecarui
  produs, deci nu se poate etichetare precisa, iar manual (754 produse) e nefezabil.
- Reguli: Fard de pleoape -> culoarea ochilor; Ruj/Luciu/Fard de obraz -> culoarea
  parului; restul 'toate' (universal).
- **Semnal slab + pondere mica (1):** majoritatea produselor raman 'toate', deci
  criteriul da puncte aproape tuturor si doar penalizeaza produsele etichetate
  clar pentru ALTA culoare. Directional corect, dar nu domina scorul - intentionat,
  dat fiind ca detectia ochilor (~63%) si parului (~72%) nu e perfecta.
- Limitare: fara nuanta reala per produs (color_hex / shade), potrivirea ramane
  aproximativa. Imbunatatire viitoare: catalog cu nuanta exacta a fiecarui produs.

## Detectia fetei

- Necesita o fata clar vizibila, cu capul relativ drept si privirea spre camera.
- O singura fata per poza (`max_num_faces=1`); intr-un grup, se ia prima
  detectata.

## Mediu de rulare

- **MediaPipe nu suporta Python 3.13+.** Aplicatia ruleaza intr-un venv cu
  Python 3.12 (`mediapipe==0.10.18`, `opencv-python==4.11.0.86`, `numpy==1.26.4`).
  Vezi `requirements.txt`.

## Analiza data de aplicatie
-Testat pe: poza test 2 
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:75.6

-Testat pe: poza test 3
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui 
-ITA:70.7
-Par:

-Testat pe: poza test 4
-Acuratete estimata: ton deschis, subton neutru
-Culoare ochi:caprui
-ITA:70.5
-Par:

-Testat pe: poza test 5
-Acuratete estimata: ton inchis, subton rece
-Culoare ochi:caprui
-ITA:-47.9
-Par:

-Testat pe: poza test 6
-Acuratete estimata: ton inchis, subton rece
-Culoare ochi:caprui
-ITA:-60.6
-Par:

-Testat pe: poza test 7
-Acuratete estimata: ton mediu, subton neutru
-Culoare ochi:caprui
-ITA:32.4
-Par:

-Testat pe: poza test 8
-Acuratete estimata: ton inchis, subton rece
-Culoare ochi:caprui
-ITA:-14.5
-Par:

-Testat pe: poza test 9
-Acuratete estimata: ton mediu, subton, neutru
-Culoare ochi:caprui
-ITA:33.8
-Par:

-Testat pe: poza test 10
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:81.4
-Par:

-Testat pe: poza test 11
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:84.5
-Par:

-Testat pe: poza test 12
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:64.7
-Par:

-Testat pe: poza test 13
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:81.8
-Par:

-Testat pe: poza test 14
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:albastri
-ITA:88.1
-Par:

-Testat pe: poza test 15
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi: caprui
-ITA:92.2
-Par:

-Testat pe: poza test 16
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:76.7
-Par:

-Testat pe: poza test 17
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:81.7
-Par:

-Testat pe: poza test 18
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:79.1
-Par:

-Testat pe: poza test 19
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:83.0
-Par:

-Testat pe: poza test 20
-Acuratete estimata: ton deschis, subton rece
-Culoare ochi:caprui
-ITA:76.9
-Par:

-Testat pe: poza test 21
-Acuratete estimata: ton deschis, subton cald
-Culoare ochi:caprui
-ITA:71.8
-Par:

-Testat pe: poza test 22
-Acuratete estimata: ton deschis, subton neutru
-Culoare ochi:caprui
-ITA:74.1
-Par: