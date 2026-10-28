"""Thin wrapper around the Instagram Graph API calls the bot needs.

Uses the "Instagram API with Instagram Login" (graph.instagram.com). If you use the
Facebook Login variant instead, set GRAPH_API_HOST=https://graph.facebook.com and use
a Page access token.
"""

import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)

COMMENT_MAX_CHARS = 2200
DM_MAX_CHARS = 1000


class InstagramClient:
    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=20)
        self.base = f"{settings.graph_api_host.rstrip('/')}/{settings.graph_api_version}"

    def _post(self, path: str, params: dict | None = None, json: dict | None = None) -> dict:
        params = {**(params or {}), "access_token": settings.ig_access_token}
        resp = self.http.post(f"{self.base}/{path}", params=params, json=json)
        if resp.status_code >= 400:
            raise RuntimeError(f"Instagram API {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    def reply_to_comment(self, comment_id: str, text: str) -> dict:
        return self._post(f"{comment_id}/replies", params={"message": text[:COMMENT_MAX_CHARS]})

    def hide_comment(self, comment_id: str) -> dict:
        return self._post(comment_id, params={"hide": "true"})

    def send_dm(self, recipient_id: str, text: str) -> dict:
        body = {"recipient": {"id": recipient_id}, "message": {"text": text[:DM_MAX_CHARS]}}
        return self._post(f"{settings.ig_user_id}/messages", json=body)

    def private_reply(self, comment_id: str, text: str) -> dict:
        """Sends a DM to the person who wrote a comment."""
        body = {"recipient": {"comment_id": comment_id}, "message": {"text": text[:DM_MAX_CHARS]}}
        return self._post(f"{settings.ig_user_id}/messages", json=body)
