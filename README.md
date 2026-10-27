# ScamShield AI

**Detect the Scam. Protect Your Money. Empower the Community.**

A working Malaysian digital safety prototype for EIS’26. React, Vite, TypeScript, Tailwind, FastAPI, SQLAlchemy and an asynchronous Telegram bot. Web and Telegram use the **same Python detection functions**.

## Windows quick start

Requirements: Python 3.11–3.14, Node.js 22.12+ (Node 24 recommended), npm. From this folder:

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

Open **http://127.0.0.1:5173**. API/OpenAPI: **http://127.0.0.1:8000/docs**. Stop script-managed servers with `.\scripts\stop.ps1`. Logs: ignored `.local/`. Setup creates `.env` only when missing, applies migrations and seeds educational/reference content without fake activity.

If local script execution is disabled, use manual commands:

```powershell
Copy-Item .env.example .env  # Only if .env does not already exist
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.cli seed
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

In another terminal, from the root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

For macOS/Linux use standard Python virtual environment creation/activation and `.venv/bin/python` instead of `.venv\Scripts\python.exe`; run the same backend commands from `backend/`. Frontend uses `npm ci` and `npm run dev`.

## Try the prototype

1. `/scan`: choose **Try a fictional example**, then analyze. Risk and explanations are computed by the backend.
2. Compare `Hello, our project meeting is at 10 today.` Low risk never means guaranteed safe.
3. `/url-checker`: try `https://maybank.verify.example.com/login` (reserved example domain) or `http://127.0.0.1/login`. The scanner **never opens submitted links**, resolves DNS or follows redirects.
4. Switch to Bahasa Melayu or dark mode. Upload a screenshot when Tesseract is installed, review/redact OCR text, then analyze it.
5. Explore learning, community insights, official resources, Telegram and project impact pages. Dashboard data is aggregate **installation activity**, including repeat/development scans, not national statistics.
6. Optionally create an account, explicitly opt into history on a scan, and delete history or the account from `/history`.

## Telegram integration

Create a BotFather bot named **ScamShield AI Bot**, choose an available username, and set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` in the ignored root `.env`. Never paste the token into chat or source control. Start the migrated API, then in another terminal:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.telegram_bot.bot
```

Supports `/start`, `/scan`, `/url`, `/help`, `/report`, `/privacy`, forwarded text, links and screenshot OCR. Private chats only, rate limits, asynchronous processing feedback, shared detection engine. OCR text is returned for review and resubmission. No raw messages or Telegram IDs are stored in our database. [BotFather/webhook setup](docs/telegram.md).

**No bot token is bundled. Live delivery needs the owner's credentials and has not been verified. Mocked tests cover handlers and consistency; the UI distinguishes configuration from verified live delivery.**

## Screenshot OCR

Install Tesseract and English language data on the backend host. Add Malay (`msa`) data for Malay extraction. On Windows set `TESSERACT_CMD` to the executable path if absent from PATH. Use `OCR_LANGUAGES=eng+msa` only when both packs exist. Docker installs both packs.

Limits: PNG/JPEG/WEBP, 5 MB, 12 megapixels, two simultaneous OCR jobs/process, 20-second timeout. Image pixels are rebuilt without metadata; temporary uploads are closed afterward. Unavailable OCR returns **503 with paste-text guidance**, never fake text. The image endpoint extracts text only; users review/redact before submitting to the text endpoint.

## Tests and build

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm.cmd test
npm.cmd run build
npm.cmd audit
# With API and Vite running on 8000 and 5173:
npx.cmd playwright install chromium
npx.cmd playwright test
```

Backend tests use an isolated in-memory database. Browser tests use the running installation, submit fictional content, delete their test accounts/history, and leave anonymous activity counters as disclosed in the dashboard. Reports/screenshots are ignored under `frontend/playwright-report/` and `frontend/test-results/`.

From the root, `.\.venv\Scripts\python.exe scripts\benchmark.py` records a fictional-input rules microbenchmark. It excludes HTTP/OCR/database/Telegram and does not measure detection accuracy.

## Administration and retention

No default admin or hardcoded password. From `backend/`, run `python -m app.cli create-admin` with your virtual-environment executable. It prompts privately for a new password. Sign in at `/login`, then open `/admin` to manage notices and English lesson text. Server authorization and audit records protect every admin change. Extended bilingual question-authoring UI remains future work.

Saved history expires after 30 days and is owner-protected. Schedule `python -m app.cli cleanup` daily for actual deletion; cleanup also runs at API startup. Account deletion cascades through sessions, history and personal quiz attempts. Anonymous counters remain. Set separate production backup expiration policies.

## Docker / PostgreSQL

```powershell
docker compose up --build -d
# Open http://localhost:8080
# After configuring a Telegram token:
docker compose --profile telegram --profile maintenance up --build -d
```

SQLite uses a persistent named volume. For PostgreSQL, set a strong URL-safe `POSTGRES_PASSWORD` in `.env`:

```powershell
docker compose -f docker-compose.yml -f docker-compose.postgres.yml --profile maintenance up --build -d
```

Do not use `down -v` unless you intend to destroy database volumes. Docker execution requires a Docker host and is separate from the verified native application. [Deployment guide](docs/deployment.md).

## AI status and limits

Active engine: **explainable-rules-v1**. Score is the capped sum of bilingual warning-indicator weights, **not fraud probability**. LOW <25, MEDIUM 25–59, HIGH ≥60. Rules can miss unfamiliar scams or flag legitimate content. Always independently verify important requests.

No approved licensed bilingual dataset is bundled, so **no trained model, validated accuracy or model confidence is claimed**. Optional experiment runners compare TF-IDF message models (Naive Bayes, logistic regression, calibrated linear SVM) and lexical URL models (logistic regression, random forest), producing held-out metrics and hash-bound candidate artifacts. Safe skops inference requires an independently reviewed report and threshold policy; web and Telegram share the guarded runtime. [ML guide](docs/ml.md).

## Project structure

```text
frontend/src/        components, pages, hooks, services, layouts, types
frontend/e2e/        desktop/mobile browser tests
backend/app/        api, core, models, schemas, services, ml, telegram_bot
backend/migrations/ versioned Alembic schema
backend/tests/      rules, API, security, OCR and mocked Telegram tests
datasets/           fictional samples and dataset policy
models/             model policy; no trained model bundled
docs/               architecture, API, security, ML, deployment and demo
scripts/            Windows setup/start/stop and rules benchmark
```

[Architecture](docs/architecture.md) · [API](docs/api.md) · [Security](docs/security.md) · [Implementation status](docs/status.md) · [Verification results](docs/verification.md) · [Competition walkthrough](docs/demo.md) · [Verified resources](docs/resources.md)

ScamShield AI is an independent student project, not a government agency or official fraud verification service. It cannot conclusively establish fraud, guarantee safety, recover funds or demonstrate reduced national scam rates. The institutional business tier is informational; billing and organization tenancy are not implemented.
