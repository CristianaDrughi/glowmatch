# Diagrame de prezentare (simplificate)

Diagrame „de slide" — fara coloane, doar ideea principala. Bune pentru
prezentarea de licenta, unde conteaza claritatea, nu detaliile.

---

## 1. Fluxul de date al aplicatiei (cum circula informatia)

> Imagine gata de pus in lucrare: [docs/diagrame/flux_date.png](docs/diagrame/flux_date.png)

![Fluxul de date](docs/diagrame/flux_date.png)

```mermaid
flowchart TD
    U([Utilizator]) -->|urca poza| AF[/analiza-foto/]
    U -->|completeaza formular| FORM[/recomandari · skincare/]

    AF --> V[vision.py<br/>computer vision]
    V -->|ton, subton, ochi, par| REC[recommender.py<br/>reguli + scoring]
    FORM -->|preferinte| REC

    DB[(SQLite<br/>app.db)] -->|catalog produse| REC
    REC -->|top 5 produse| RES[results.html]
    REC -->|salveaza istoric| DB
    V -->|audit, fara poza| DB

    RES -->|daca exista email| WH[webhook_dispatcher.py]
    WH -->|POST JSON| N8N[n8n cloud]
    N8N -->|AI Agent Gemini| MAIL([Email catre utilizator])

    RES --> U
```

### Varianta ASCII

```
   ┌─────────────┐
   │ Utilizator  │
   └──────┬──────┘
          │ urca poza / completeaza formular
          ▼
   ┌──────────────────────────────────────────┐
   │              app.py (Flask)               │
   └───┬───────────────────────┬───────────────┘
       │ poza                  │ preferinte
       ▼                       │
 ┌───────────┐                 │
 │ vision.py │ ton/subton/     │
 │  (CV+ITA°)│ ochi/par        │
 └─────┬─────┘                 │
       │                       ▼
       │              ┌────────────────┐      ┌──────────────┐
       └─────────────►│ recommender.py │◄─────│   app.db     │
                      │ reguli+scoring │      │  (catalog)   │
                      └───────┬────────┘      └──────────────┘
                              │ top 5 produse
                              ▼
                      ┌────────────────┐
                      │  results.html  │──► afisat utilizatorului
                      └───────┬────────┘
                              │ daca a dat email
                              ▼
                  ┌──────────────────────┐
                  │ webhook_dispatcher.py│──► n8n ──► AI (Gemini) ──► Email
                  └──────────────────────┘
```

---

## 2. Arhitectura pe straturi (ce piesa unde sta)

```mermaid
flowchart TB
    subgraph PREZENTARE["Prezentare (UI)"]
        T[templates/ HTML]
        S[static/ CSS + poze]
    end

    subgraph APLICATIE["Logica aplicatiei"]
        APP[app.py rute publice]
        ADMIN[admin.py + auth.py zona admin]
        REC[recommender.py]
        VIS[vision.py]
        WH[webhook_dispatcher.py]
        REP[reports.py]
    end

    subgraph DATE["Date"]
        DBM[db.py schema + acces]
        DBF[(app.db SQLite)]
    end

    EXT[n8n / Gemini email]

    PREZENTARE --- APP
    PREZENTARE --- ADMIN
    APP --> REC
    APP --> VIS
    APP --> WH
    ADMIN --> REP
    REC --> DBM
    REP --> DBM
    VIS --> DBM
    WH --> DBM
    WH --> EXT
    DBM --> DBF
```

---

## 3. Schema BD simplificata (doar tabelele + relatiile)

Pentru cand vrei doar legaturile, fara lista de coloane.

```mermaid
erDiagram
    recommendations_log ||--o{ recommendation_products : are
    products            ||--o{ recommendation_products : apare_in
    recommendations_log ||--o{ outbound_webhooks       : declanseaza

    admin_users {
        x independent
    }
    extraction_log {
        x audit_foto
    }
    test_cases {
        x evaluare
    }
```

### Varianta ASCII

```
   recommendations_log ──1──N── recommendation_products ──N──1── products
            │
            └──1──N── outbound_webhooks

   (independente, fara relatii)
   admin_users      extraction_log      test_cases
```
