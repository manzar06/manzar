# Instagram auto-replier (Claude)

A bot that reads new Instagram comments and DMs, uses Claude to understand each one, and
replies automatically.

For every comment or DM, Claude decides:

| Field | Values |
|---|---|
| sentiment | positive / neutral / negative |
| intent | question, praise, complaint, purchase_interest, collaboration, spam, abuse, other |
| action | `reply`, `hide` (spam or abuse comments only), or `ignore` |
| reply | the public comment reply, or the DM reply |
| private_reply | for comments: a DM sent privately to the commenter (prices, orders, personal questions) |

Claude only states facts written in `business_profile.md`, so fill that file in first.

## How it works

```
Instagram ──webhook──▶ /webhook (FastAPI) ──▶ Claude analyzes ──▶ Instagram API posts the reply
                                    │
                                    └─▶ SQLite: de-duplication, DM history, rate limit, action log
```

Built-in safeguards:
- **Dry run by default:** `DRY_RUN=true` decides and logs but posts nothing.
- **No reply loops:** the bot's own replies and echoed DMs are skipped.
- **No double replies:** each comment or DM is handled once, even if Instagram delivers the webhook twice.
- **Hourly cap:** `MAX_REPLIES_PER_HOUR` limits how many replies go out.
- **Prompt-injection guard:** comments are treated as content, never as instructions.
- **Signature check:** every webhook must be signed by your Meta app.
- **DM memory:** the last 10 messages with a person are passed to Claude, so it knows the context of the conversation.

## 1. Try the analyzer (needs only a Claude API key)

```bash
pip install -r requirements.txt
cp .env.example .env          # put your ANTHROPIC_API_KEY in it
python -m igbot.try_it "How much is the blue hoodie?"
python -m igbot.try_it --dm "my order hasn't arrived, it's been 2 weeks"
```

## 2. Set up Instagram (Meta)

Meta changes these screens often, so check the current docs at
developers.facebook.com → Instagram Platform → "Instagram API with Instagram Login".

1. Switch your Instagram account to a **Professional** account (Business or Creator).
2. Create an app at developers.facebook.com and add the **Instagram** product.
3. Under "API setup with Instagram login", add your account and generate an
   **access token**. Note your **Instagram user ID** too.
4. The token needs these permissions: `instagram_business_basic`,
   `instagram_business_manage_comments`, `instagram_business_manage_messages`.
5. Copy the **App secret** from App settings → Basic.
6. Put the token, user ID and app secret in `.env`, and pick any random string for `IG_VERIFY_TOKEN`.
7. Deploy the bot somewhere with a public HTTPS URL (see step 3 below).
8. In the app's **Webhooks** settings, set the callback URL to `https://YOUR-DOMAIN/webhook`,
   enter the same verify token, and subscribe to the **comments** and **messages** fields.
9. To receive comments and DMs from the public, not just from yourself, Meta usually
   requires the app to be **Live** and to pass **App Review** for those permissions.

Instagram rules to know about:
- You can only DM someone within **24 hours** of their last message to you.
- A private reply to a comment is allowed **once per comment**, within 7 days.
- Long-lived access tokens expire after about **60 days**, so refresh yours before then.
- If calls fail with a version error, update `GRAPH_API_VERSION` in `.env` to the current version.

## 3. Run it

```bash
uvicorn igbot.server:app --host 0.0.0.0 --port 8000
```

- For testing on your own computer, `ngrok http 8000` gives you a temporary public HTTPS URL.
- For 24/7 use, deploy it to a host like Render, Railway or Fly.io.

Endpoints:
- `GET /health`: shows the status, the model and whether dry run is on.
- `GET /log`: shows recent decisions. Check this during dry run. Don't leave it public without adding auth.

When the decisions in `/log` look right, set `DRY_RUN=false` and restart.

## Cost

Each message costs one Claude call. These are estimates at `IGBOT_EFFORT=low`:

| `IGBOT_MODEL` | Per message | Messages per $100 |
|---|---|---|
| `claude-opus-5-5` (default) | ~$0.02 | ~5,000 |
| `claude-sonnet-5-5` | ~$0.01 | ~10,000 |
| `claude-haiku-5-5` | ~$0.0005 | ~200,000 |

- For a busy account, try `claude-sonnet-5-5` or `claude-haiku-5-5` and compare the replies in dry run.
- Set a monthly spend limit at platform.claude.com → Settings → Limits.
- The bot uses Claude's server-side refusal fallback (`fallbacks: "default"`). If a
  safety classifier declines a message, the API retries it once on Anthropic's
  recommended fallback model.

## Tests

```bash
pip install pytest
python -m pytest -q
```
