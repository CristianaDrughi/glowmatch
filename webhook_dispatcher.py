"""Trimite asincron payload-ul de recomandare catre webhook-ul n8n.

Workflow:
  1. Aplicatia genereaza recomandarile pentru utilizator.
  2. Daca utilizatorul a furnizat un email, apeleaza trimite_webhook(payload).
  3. Functia porneste un thread separat care face POST la N8N_WEBHOOK_URL,
     fara sa blocheze raspunsul HTTP catre browser.
  4. Indiferent de rezultat, fiecare apel este logat in tabela
     outbound_webhooks (status: success / error / skipped).

Daca N8N_WEBHOOK_URL nu este setat, apelul este sarit dar logat ca 'skipped',
util in dezvoltare pentru a vedea ce s-ar fi trimis.
"""

import json
import threading
import time
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

import config
from db import get_db


MAX_RESPONSE_LEN = 1000  # caractere logate din raspunsul webhook-ului


def _logheaza(log_id, email, url, payload, status, response_body, error, durata_ms):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO outbound_webhooks
                (log_id, email, url, payload_json, status, response_body, error, durata_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id, email, url,
            json.dumps(payload, ensure_ascii=False),
            status,
            response_body[:MAX_RESPONSE_LEN],
            error[:MAX_RESPONSE_LEN],
            durata_ms,
        ))


def _executa_post(log_id, email, payload, url, timeout):
    inceput = time.time()
    status = 'pending'
    response_body = ''
    error = ''
    try:
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        # Auth: trimitem un token Bearer ca webhook-ul n8n sa accepte doar
        # apelurile aplicatiei (configureaza Header Auth in nodul Webhook n8n).
        if config.N8N_WEBHOOK_TOKEN:
            headers['Authorization'] = f'Bearer {config.N8N_WEBHOOK_TOKEN}'
        req = urlrequest.Request(
            url,
            data=data,
            headers=headers,
            method='POST',
        )
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            status = 'success' if resp.status < 400 else 'error'
            response_body = resp.read().decode('utf-8', errors='replace')
    except HTTPError as e:
        status = 'error'
        error = f'HTTP {e.code}: {e.reason}'
    except URLError as e:
        status = 'error'
        error = f'Conexiune esuata: {e.reason}'
    except Exception as e:
        status = 'error'
        error = f'{type(e).__name__}: {e}'

    durata_ms = int((time.time() - inceput) * 1000)
    _logheaza(log_id, email, url, payload, status, response_body, error, durata_ms)


def trimite_webhook(payload: dict, email: str = '', log_id: int | None = None) -> str:
    """Trimite payload-ul la n8n in background (fire-and-forget).

    Returneaza statusul initial: 'dispatched' daca s-a pornit thread-ul,
    'skipped' daca nu e configurat URL-ul.
    """
    url = config.N8N_WEBHOOK_URL
    timeout = config.N8N_WEBHOOK_TIMEOUT

    if not url:
        _logheaza(
            log_id, email, '', payload,
            status='skipped',
            response_body='',
            error='N8N_WEBHOOK_URL nu este configurat in config.py',
            durata_ms=0,
        )
        return 'skipped'

    thread = threading.Thread(
        target=_executa_post,
        args=(log_id, email, payload, url, timeout),
        daemon=True,
    )
    thread.start()
    return 'dispatched'
