"""Turns Instagram webhook payloads into analyses and replies."""

import logging

from . import store
from .analyzer import analyze
from .config import settings
from .instagram import InstagramClient

log = logging.getLogger(__name__)

_ig: InstagramClient | None = None


def ig() -> InstagramClient:
    global _ig
    if _ig is None:
        _ig = InstagramClient()
    return _ig


def process_payload(payload: dict) -> None:
    if payload.get("object") != "instagram":
        return
    for entry in payload.get("entry", []):
        own_ids = {settings.ig_user_id, str(entry.get("id", ""))} - {""}
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                _safe(handle_comment, change.get("value", {}), own_ids)
        for event in entry.get("messaging", []):
            if "message" in event:
                _safe(handle_dm, event, own_ids)


def _safe(fn, *args) -> None:
    try:
        fn(*args)
    except Exception:
        log.exception("Failed to handle %s", fn.__name__)


def _may_post() -> bool:
    return store.posts_last_hour() < settings.max_replies_per_hour


def handle_comment(value: dict, own_ids: set[str]) -> None:
    comment_id = value.get("id")
    text = (value.get("text") or "").strip()
    author = value.get("from", {})
    # Our own replies come back as comment webhooks too; answering them would loop forever.
    if not comment_id or not text or str(author.get("id")) in own_ids:
        return
    if not store.claim(f"comment:{comment_id}"):
        return

    result = analyze("comment", text, username=author.get("username", ""))
    record = dict(kind="comment", event_id=comment_id, user=author.get("username"), text=text,
                  **vars(result), posted=0, error=None)

    if result.action == "ignore":
        pass
    elif settings.dry_run:
        record["error"] = "dry run"
    elif not _may_post():
        record["error"] = "hourly reply limit reached"
    else:
        try:
            if result.action == "hide":
                ig().hide_comment(comment_id)
            else:
                if result.reply:
                    ig().reply_to_comment(comment_id, result.reply)
                if result.private_reply:
                    ig().private_reply(comment_id, result.private_reply)
            record["posted"] = 1
        except Exception as e:
            record["error"] = str(e)
            log.error("Posting failed for comment %s: %s", comment_id, e)

    store.log_action(**record)
    log.info("comment %s @%s -> %s (%s)", comment_id, author.get("username"), result.action, record["error"] or "ok")


def handle_dm(event: dict, own_ids: set[str]) -> None:
    message = event.get("message", {})
    sender_id = str(event.get("sender", {}).get("id", ""))
    text = (message.get("text") or "").strip()
    # is_echo = a message the account itself sent.
    if message.get("is_echo") or not sender_id or sender_id in own_ids or not text:
        return
    if not store.claim(f"dm:{message.get('mid')}"):
        return

    history = store.dm_history(sender_id)
    store.add_dm(sender_id, "user", text)
    result = analyze("dm", text, history=history)
    record = dict(kind="dm", event_id=message.get("mid"), user=sender_id, text=text,
                  **vars(result), posted=0, error=None)

    if result.action != "reply" or not result.reply:
        pass
    elif settings.dry_run:
        record["error"] = "dry run"
    elif not _may_post():
        record["error"] = "hourly reply limit reached"
    else:
        try:
            ig().send_dm(sender_id, result.reply)
            store.add_dm(sender_id, "assistant", result.reply)
            record["posted"] = 1
        except Exception as e:
            record["error"] = str(e)
            log.error("Sending DM to %s failed: %s", sender_id, e)

    store.log_action(**record)
    log.info("dm %s -> %s (%s)", sender_id, result.action, record["error"] or "ok")
