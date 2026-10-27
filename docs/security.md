# Privacy and security

Implemented controls:

- URL checks never open the submitted destination, resolve it, or follow its redirects. When explicitly configured, the backend sends the exact URL as form data only to the fixed HTTPS PhishTank API endpoint for a reputation lookup, with a four-second timeout and redirects disabled.
- Pydantic input lengths, HTTP(S)-only URLs, domain/IP/IDNA checks. React escapes submitted text; no raw HTML rendering.
- Request-body limits including chunked uploads before multipart parsing, real image decoding, byte/pixel limits, two OCR slots/process, timeout, rebuilt pixels without metadata, temporary file closure.
- Argon2 hashes, dummy hash verification for unknown accounts, random session tokens, hashed server-side tokens, eight-hour expiry, logout revocation, HttpOnly/SameSite=strict cookies. Production enables Secure cookies and HSTS.
- Explicit allowed origins and required non-simple header for every mutation. Prevents cross-origin browser forms from mutating cookie-authenticated data. No wildcard credential CORS.
- Server role/ownership checks; another owner's scan returns 404. Public registration cannot assign administrator role. No default admin credentials.
- Bounded in-memory rate limits with salted keys, no saved raw identity. Structured request logs contain route template/status/duration, excluding request content, cookies, tokens, query strings and IPs. Telegram HTTP logging is suppressed to avoid token URLs.
- Parameterized ORM queries, referential integrity, deletion cascades, atomic aggregate upserts.
- Guest non-retention, opt-in private history, 30-day expiry, startup cleanup and scheduled daily cleanup command. Anonymous aggregates remain. Active SQLite deletion uses secure_delete.
- Environment secrets only; private database/environment/model files are ignored. No third-party AI processing. PhishTank receives website-checker URLs only when its integration is configured; the UI and privacy notice disclose this transfer.

Production responsibilities: deploy HTTPS, protect database/application ports, restrict operator access, encrypt storage/backups, expire backups, schedule daily cleanup, and configure proxy logs to exclude sensitive data. Deletion cannot erase backups or OS snapshots outside the active database.

Use a gateway/distributed rate limiter for multiple processes. The included backend does not trust arbitrary X-Forwarded-For; behind Nginx it may conservatively group visitors under the proxy IP. Add trusted gateway per-client limits for real deployments.

Expose Telegram only behind HTTPS with a secret-token header preserved to python-telegram-bot. The default compose bot exposes no webhook port; add a gateway route to internal port 8081. Never place the bot token in a path/log/command.

Known detection limits: keyword evasion, compromised legitimate sites, split-image content, OCR mistakes, legitimate alternative official domains, and negation/context. Credential-negation handling recognizes common English/Malay safety advice only. Language detection is lexical. HTTPS and low scores do not establish safety. Tests verify implementation, not real-world detection validity. No audited production-security or national-impact claim is made.
