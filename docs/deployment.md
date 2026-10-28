# Deployment

## Vercel Services

The root `vercel.json` defines two services in one Vercel project:

- `backend`: FastAPI from `backend/`, publicly routed at `/api/*`.
- `frontend`: Vite from `frontend/`, publicly routed for all remaining paths.

The browser uses same-origin `/api/v1/*` requests, so there is no server-side
service-to-service call and no service binding. Vercel bindings are runtime-only
and cannot be consumed by a static Vite build or browser code. Services routing
preserves the `/api` prefix, matching FastAPI's existing `/api/v1` routes.

Before deployment, set `ENVIRONMENT=production` and a managed PostgreSQL
`DATABASE_URL` in Vercel Project Settings. SQLite and local filesystems are not
durable serverless storage. Apply Alembic migrations to that database from a
trusted administrative environment before serving traffic. Do not set
`VITE_API_BASE_URL`; the frontend should use the shared deployment origin.

If `DATABASE_URL` is absent, the API starts with an explicitly non-durable
SQLite database in Vercel's writable `/tmp` scratch directory. This keeps guest
scanning and educational content available for demos, but accounts, history,
metrics, and administrative changes can disappear whenever the function
instance is recycled. The health response reports `"storage":"ephemeral"` in
this mode. Configure and migrate PostgreSQL before relying on persistence.

Server OCR requires a Tesseract executable and language packs. The standard
Vercel Python function does not install the repository's Docker image packages,
so the web screenshot scanner falls back to on-device Tesseract.js OCR in the
browser. The backend endpoint still returns its documented 503 response, and
Telegram screenshot OCR still requires a container service with Tesseract. The Telegram
polling process is not included as a Vercel service because it is a continuous
worker; deploy it separately or implement an HTTPS webhook function.

Run all declared services locally with `vercel dev -L` after installing the
Vercel CLI.

## Local Docker stack

Install Docker Engine/Desktop with Compose, then from the project root run `docker compose up --build -d`. Frontend: http://localhost:8080; backend docs: http://127.0.0.1:8000/docs. Database volumes persist across restarts. The non-root Python backend includes English/Malay Tesseract language data. Nginx serves the React build, rewrites deep routes and proxies `/api/` to FastAPI with a 6 MB request limit and security headers.

Configure your private `.env` before `--profile telegram`; use `--profile maintenance` to run daily retention cleanup. Profiles are optional so missing bot credentials do not break web startup.

For PostgreSQL set a strong URL-safe POSTGRES_PASSWORD and use:

```text
docker compose -f docker-compose.yml -f docker-compose.postgres.yml --profile maintenance up --build -d
```

Use the same database configuration for API, Telegram and cleanup. Reference/learning data is seeded idempotently without fake activity. API startup applies Alembic migrations. For an admin run `docker compose exec backend python -m app.cli create-admin` interactively. Back up the database and test restoration before schema upgrades. Never destroy volumes unintentionally.

Docker is unavailable in the implementation workspace; native startup, tests and production asset build were exercised. Build/run the containers and PostgreSQL override on a Docker host before claiming those environments verified.

## Render / Railway / Docker-compatible hosts

1. Provision managed PostgreSQL and set DATABASE_URL with the SQLAlchemy `postgresql+psycopg://` scheme. Use provider TLS parameters as required.
2. Deploy `backend/Dockerfile`, set ENVIRONMENT=production, exact CORS_ORIGINS, retention configuration, and bot credentials in the platform secret store. Do not add credentials to build args or source.
3. Run migrations once as a release command before starting API workers. The default Docker command also migrates for a single-instance prototype. Coordinate migration execution before horizontal scaling.
4. Serve API and frontend through the same HTTPS origin/reverse proxy when using the included SameSite=strict cookie flow. This avoids cross-site cookie issues. Arbitrary unrelated frontend/backend domains are not a drop-in authenticated deployment.
5. Build frontend with `npm ci && npm run build`, serve `frontend/dist`, and rewrite every non-asset/non-API application route to index.html. Vite dev proxy is development-only. For separate static hosting, configure a same-origin `/api/` gateway to your Python backend. VITE_API_BASE_URL is public build-time configuration, never a secret.
6. Firebase Hosting can serve the static build, but requires an appropriate same-origin backend rewrite/gateway (for example a supported managed HTTPS backend); it cannot itself run FastAPI or Telegram. Do not publish a frontend and present offline backend features as active.
7. Configure HTTPS, encrypted storage/backups, backup expiration, operator permissions, gateway rate limits, safe logs and daily `python -m app.cli cleanup`.
8. Run one Telegram worker per bot token. Polling works on an always-on worker; production webhook mode needs its own HTTPS route to internal port 8081. See telegram.md.
9. Check `/api/v1/health`, test guest and authenticated flows over HTTPS, verify Secure cookies, history ownership/deletion, real OCR, and actual Telegram delivery.

The included API limiter is per-process and does not trust spoofed forwarded IPs. Behind a gateway it may group users under the proxy address. Add trusted gateway/distributed client limits before scaling. The default local compose exposes ports on loopback; use a dedicated HTTPS ingress for public deployment rather than simply exposing HTTP ports.
