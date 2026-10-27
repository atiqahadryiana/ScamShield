# API contract

Base `/api/v1`. Typed OpenAPI at `/docs`; raw schema at `/openapi.json` on the API host.

All POST/PUT/DELETE requests require `X-ScamShield-Client: web`. Browsers must use an allowed Origin. JSON requests use Content-Type application/json; images use multipart `file`. Bodies over 6 MB, including chunked requests, are rejected before multipart parsing.

| Endpoint | Access | Input → output |
| --- | --- | --- |
| GET `/health` | Guest | Engine/database/OCR/configured bot status; never token |
| POST `/scan/text` | Guest; account to save | `{text,save_history:false}` → Assessment; text 3–10000 chars |
| POST `/scan/url` | Guest; account to save | `{url,save_history:false}` → Assessment; URL 4–2048 chars |
| POST `/scan/image` | Guest | Multipart image → `{extracted_text,requires_review:true,retained:false}` |
| GET `/scan/{id}` | Owner | Stored unexpired Assessment; 404 for other owners |
| POST `/auth/register` | Guest | `{email,password}` → user + session cookie; password 10–128 chars |
| POST `/auth/login` | Guest | Same credentials → user + session cookie |
| GET `/auth/me` | Account | Own email, ID, role, preferences |
| PUT `/auth/preferences` | Account | `{dashboard_days:7 or 30}` → user with saved chart preference |
| POST `/auth/logout` | Guest/account | Revoke token, clear cookie |
| DELETE `/auth/account` | Account | Delete account and linked private records |
| GET `/history` | Account | Last 100 own unexpired opted-in scans |
| DELETE `/history` | Account | Delete own saved history |
| GET `/education/modules` | Guest | Lessons and question options; answers withheld |
| POST `/education/quiz` | Guest/account | `{module_id,answers:[optionIndex],stage:'pre'|'post'}` → trusted grade/explanation |
| GET `/education/progress` | Account | Own quiz attempts |
| GET `/dashboard/summary` | Guest | Coarse daily aggregates, quiz aggregates, public notices |
| GET `/resources` | Guest | Verified official website links; no government API |
| GET `/admin/overview` | Admin | Aggregate overview, account count, recent audits |
| POST `/admin/notices` | Admin | `{title,body}` → notice ID, audit |
| DELETE `/admin/notices/{id}` | Admin | Delete notice and record audit |
| PUT `/admin/modules/{id}` | Admin | `{title,body}` → update English title/lesson and audit |

Assessment: UUID `id`, LOW/MEDIUM/HIGH `risk`, 0–100 `score`, score type, optional validated `model_probability`, engine, language en/ms/und, primary category, indicators with bilingual titles/explanations/weights, bilingual recommendations/disclaimers, ISO timestamp, optional domain, and threat-intelligence status. Without reviewed artifacts, `score_type` is `heuristic_indicator_score`, `model_probability` is null, and `engine` is `explainable-rules-v1`. With a reviewed model and threshold policy, the score is the model probability expressed as a percentage while rule indicators remain as explanations.

Risk indicators are deterministic for the same normalized input; IDs/timestamps differ. Language identification uses lexical cues and is not validated NLP. No probability or measured accuracy is implied. Telegram calls the same analyzer functions directly.

```powershell
$body = @{text='Congratulations! Pay RM50 registration fee immediately.';save_history=$false} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/scan/text -Headers @{'X-ScamShield-Client'='web'} -ContentType application/json -Body $body
```

Errors: `{error:{code,message,fields?}}`; submitted values are excluded. Statuses: 401 sign-in, 403 origin/header/role, 404 absent/expired/other owner, 409 duplicate account, 413 oversized, 422 invalid input, 429 rate limit (Retry-After:60), 503 OCR unavailable. Sessions expire in 8 hours. Default limits: 30 mutation requests/minute/address, 10 auth writes/minute/address, 15 bot messages/minute/private chat. Deploy a gateway/distributed limiter when scaling beyond one process.
