# BotFather and webhook setup

1. Open the verified `@BotFather` account in Telegram and run `/newbot`.
2. Choose display name **ScamShield AI Bot** and an available username ending in `bot`.
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` (without @) in ignored root `.env`. Never share/commit the token; revoke it through BotFather if exposed.
4. Use `/setcommands`:

```text
start - Welcome and supported functions
scan - Check a suspicious message
url - Check a website address
help - Instructions and limitations
report - Official Malaysian safety resources
privacy - Processing and retention information
```

5. Migrate/seed the database, start the API, then run `python -m app.telegram_bot.bot` from `backend/` using the project virtual environment. The API and bot must use the same DATABASE_URL.
6. Send `/start` in a private chat, forward a fictional sample from `datasets/samples.json`, and compare risk/score/indicators against the website. IDs and timestamps differ by request.
7. Upload a screenshot ≤5 MB. Review/redact the returned OCR text and send the reviewed text back for assessment. Tesseract is required; Docker includes eng/msa packs.

One polling process per token. No token is bundled. Configuration presence is not proof of live connectivity. Mocked tests cannot establish actual Telegram delivery. Telegram independently retains/processes conversations under its own privacy policy.

## Production webhooks

Set `TELEGRAM_WEBHOOK_URL=https://your-bot-host.example` and a secure `TELEGRAM_WEBHOOK_SECRET` of 32–256 characters using only A–Z, a–z, 0–9, `_`, `-`. The bot appends `/telegram` and listens on internal TELEGRAM_PORT (default 8081).

python-telegram-bot's `run_webhook` registers the URL and validates the Telegram secret-token header. Terminate TLS at a trusted gateway forwarding only `/telegram`, preserving `X-Telegram-Bot-Api-Secret-Token`. Expose the gateway rather than the raw port. Default compose is local polling; provision an HTTPS proxy route for webhooks. Do not run polling and webhook workers simultaneously for the same bot.

Results use reply_text in the originating private chat. Groups are rejected with privacy guidance. Forwarded text uses the same handler. Rate keys are temporary salted hashes; messages, IDs, usernames and screenshots are not stored in our database. No pending OCR user state is retained. Unsupported files and exceptions receive safe explanations; logs contain only error classes.
