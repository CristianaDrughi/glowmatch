"""Configurarea aplicatiei.

Editeaza valorile de mai jos direct (sau supra-scrie cu variabile de mediu).
Pentru un proiect de productie, ar trebui sa pui SECRET_KEY si N8N_WEBHOOK_URL
in variabile de mediu sau intr-un fisier .env separat.
"""

import os

# URL-ul complet al webhook-ului n8n.
# Lasa gol pana cand ai contul n8n configurat (Sprint 9).
# Exemplu: https://your-instance.app.n8n.cloud/webhook/makeup-recomandare
N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL', '').strip()

# Timeout in secunde pentru apelul webhook
N8N_WEBHOOK_TIMEOUT = int(os.environ.get('N8N_WEBHOOK_TIMEOUT', '10'))

# Token secret trimis ca 'Authorization: Bearer <token>' catre webhook-ul n8n.
# Configureaza aceeasi valoare in nodul Webhook n8n (Authentication: Header Auth).
# Lasa gol = fara auth (webhook deschis).
N8N_WEBHOOK_TOKEN = os.environ.get('N8N_WEBHOOK_TOKEN', '').strip()

# Cheia secreta Flask pentru session cookies.
# In productie, schimba cu o valoare random lunga.
SECRET_KEY = os.environ.get(
    'FLASK_SECRET_KEY',
    'licenta-makeup-recomandare-secret-2026',
)
