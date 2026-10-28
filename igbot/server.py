"""Webhook server. Run with: uvicorn igbot.server:app --host 0.0.0.0 --port 8000"""

import hashlib
import hmac
import json
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from . import store
from .config import settings
from .handler import process_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Instagram auto-replier")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "dry_run": settings.dry_run, "model": settings.claude_model}


@app.get("/webhook")
def verify(request: Request) -> PlainTextResponse:
    """Meta calls this once when you register the webhook URL."""
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and settings.ig_verify_token and hmac.compare_digest(
        q.get("hub.verify_token", ""), settings.ig_verify_token
    ):
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verification failed")


def signature_ok(body: bytes, header: str | None) -> bool:
    if not settings.ig_app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(settings.ig_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header.removeprefix("sha256="), expected)


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks) -> dict:
    body = await request.body()
    if not signature_ok(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=401, detail="bad signature")
    # Answer Meta right away; Claude and the replies run after the response is sent.
    background.add_task(process_payload, json.loads(body))
    return {"ok": True}


@app.get("/log")
def action_log(limit: int = 50) -> list[dict]:
    """Recent decisions. Don't expose this publicly without adding auth."""
    return store.recent_actions(limit)
