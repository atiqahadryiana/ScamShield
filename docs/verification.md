# Verification record

Date: **15 October 2026**. Native Windows workspace, Python 3.14.2, Node 24.13.0, npm 11.6.2.

| Check | Observed result |
| --- | --- |
| Backend pytest, optional ML dependencies installed | **33 passed**, no skipped tests or warnings |
| React Testing Library / Vitest | **3 passed** |
| Playwright desktop + mobile Chromium | **14 passed** |
| TypeScript + Vite production build | Passed; lazy-loaded secondary pages/charts |
| npm audit | **0 vulnerabilities** at verification |
| Alembic upgrade/check | Initial schema applied; no missing model operations detected |
| API and frontend native startup | Health status ok; frontend HTTP 200 |
| Windows managed start/stop/restart | Exercised; handles virtualenv interpreter child processes |
| Rules microbenchmark | See benchmark.json; 1000 fictional text/URL pairs; no HTTP/OCR/ML included |

Tests cover bilingual dynamic risk, negative credential-safety context, Unicode normalization, URL lexical features/no DNS, validation, private history ownership and expiry, cleanup/deletion/cascades, CSRF/origin/header guards, rate limits, request sizes, server-side quiz grading, admin roles/audits, mocked OCR review/failure, Telegram shared results/private boundaries/image review, and dataset deduplication/candidate training plumbing.

The optional ML smoke test creates explicitly synthetic data and a temporary candidate only inside pytest's temporary directory. It asserts `validated:false` and the inference approval gate. No model or synthetic accuracy claim is shipped or activated.

Browser tests exercised the real running API and UI, including BM, dark mode, mobile navigation/escape focus, live results, quizzes, and private account/history deletion. They submit fictional content; anonymous counts therefore include development activity, as the dashboard discloses. Source screenshots are in ignored frontend/test-results.

Not exercised externally: live Telegram delivery (no token), real Tesseract OCR (executable absent), Docker/PostgreSQL (Docker absent), production HTTPS/webhook routing, authorized-data model validation, usability study and digital-literacy impact. Their implementation/configuration status is recorded in status.md. Mocked OCR or Telegram tests do not prove external integration availability.
