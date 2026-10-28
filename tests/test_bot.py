import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from igbot import handler, store
from igbot.analyzer import Analysis
from igbot.config import settings
from igbot.server import app


class FakeIG:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        return lambda *args: self.calls.append((name, *args))


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    store._conn = None
    fake = FakeIG()
    monkeypatch.setattr(handler, "_ig", fake)
    monkeypatch.setattr(settings, "dry_run", False)
    analyses = []

    def fake_analyze(kind, text, username="", history=None):
        analyses.append((kind, text, history))
        return Analysis("positive", "question", "reply", "Thanks!", "Sent details", "test")

    monkeypatch.setattr(handler, "analyze", fake_analyze)
    return fake, analyses


def comment_payload(author_id="123", comment_id="c1"):
    return {"object": "instagram", "entry": [{"id": "999", "changes": [{"field": "comments", "value": {
        "id": comment_id, "text": "how much?", "from": {"id": author_id, "username": "bob"}}}]}]}


def dm_payload(sender="123", mid="m1", echo=False):
    msg = {"mid": mid, "text": "hello"}
    if echo:
        msg["is_echo"] = True
    return {"object": "instagram", "entry": [{"id": "999", "messaging": [
        {"sender": {"id": sender}, "recipient": {"id": "999"}, "message": msg}]}]}


def test_comment_gets_public_and_private_reply(fresh):
    fake, _ = fresh
    handler.process_payload(comment_payload())
    assert fake.calls == [("reply_to_comment", "c1", "Thanks!"), ("private_reply", "c1", "Sent details")]


def test_own_comment_and_duplicates_are_skipped(fresh):
    fake, analyses = fresh
    handler.process_payload(comment_payload(author_id="999"))
    handler.process_payload(comment_payload(comment_id="c2"))
    handler.process_payload(comment_payload(comment_id="c2"))
    assert len(analyses) == 1


def test_dm_echo_skipped_and_history_kept(fresh):
    fake, analyses = fresh
    handler.process_payload(dm_payload(echo=True))
    handler.process_payload(dm_payload(mid="m1"))
    handler.process_payload(dm_payload(mid="m2"))
    assert fake.calls == [("send_dm", "123", "Thanks!")] * 2
    assert analyses[1][2] == [("user", "hello"), ("assistant", "Thanks!")]


def test_dry_run_posts_nothing(fresh, monkeypatch):
    fake, _ = fresh
    monkeypatch.setattr(settings, "dry_run", True)
    handler.process_payload(comment_payload())
    assert fake.calls == []
    assert store.recent_actions()[0]["error"] == "dry run"


def test_webhook_signature_and_verification():
    client = TestClient(app)
    body = json.dumps({"object": "other"}).encode()
    good = "sha256=" + hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=bad"}).status_code == 401
    assert client.post("/webhook", content=body, headers={"X-Hub-Signature-256": good}).status_code == 200
    ok = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "test-verify", "hub.challenge": "42"})
    assert ok.text == "42"
    assert client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x"}).status_code == 403
