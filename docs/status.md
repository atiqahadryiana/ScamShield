# Implementation and verification status

| Capability | Status |
| --- | --- |
| React/Vite/TypeScript/Tailwind/Lucide frontend | Implemented; native production build and browser checks exercised |
| Message scan with real FastAPI response | Implemented; heuristic scores/explanations computed dynamically |
| Lexical URL checks | Implemented; no network fetch, DNS or redirects |
| Shared web/Telegram engine | Implemented; same imported functions; API and mocked handler tests |
| Telegram text/forward/link commands | Implemented; live delivery needs owner's BotFather token |
| Telegram screenshot/unsupported attachment handling | Implemented; OCR needs host Tesseract; review/resubmit flow |
| Polling / secret-verified webhook mode | Implemented; external webhook/Telegram infrastructure not exercised |
| Screenshot OCR with safe limits | Implemented; mocked integration tests; local Tesseract absent, explicit 503 fallback; Docker installs eng/msa |
| English/Bahasa Melayu interface and rule explanations | Implemented for core flows; some administrator/technical labels and quiz explanations remain English |
| Learning modules, pre/post quizzes, device progress | Implemented; server grading, fictional scenarios, account-linked attempts available through API |
| Aggregate awareness dashboard | Implemented using installation counters; no fabricated national statistics |
| Guest + optional accounts and private history | Implemented; Argon2/session/ownership/consent/deletion |
| Administrator role/content/notices/audits | Implemented; English lesson editing; no default credentials |
| Database models and Alembic migration | Implemented; SQLite tested; PostgreSQL support/compose supplied but not run here |
| ML training/evaluation and safe inference loader | Candidate preparation implemented; no approved dataset, trained model or active model probability |
| Threat intelligence / remote redirect inspection | Optional PhishTank exact-URL lookup; redirect inspection remains disabled |
| Official Malaysian resources | Verified website links; no invented agency APIs |
| SDG/business model pages | Implemented; goals distinct from installation measurements; institutional tier proposed |
| HTTPS/Docker/production deployment configuration | Supplied and documented; Docker unavailable here; no remote deployment claimed |
| Dataset validation / usability pilot / measured literacy gain | Pending actual study and authorized data |
| Billing / organizational tenancy / multi-question authoring | Deliberately outside this MVP |

Before a live competition demonstration: set and test the bot token/username, install Tesseract or use the Docker host, run a fresh rehearsal, and disclose the rule-based baseline. Before public production: verify the container/PostgreSQL stack, HTTPS/gateway settings, retention schedule/backups and conduct a security/usability pilot.
