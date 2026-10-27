# ML preparation and limitations

The default engine is transparent rules. **No trained model or validation dataset is bundled.** UI/API report heuristic indicators with model_probability=null. The project does not claim calibrated confidence, accuracy, precision/recall, financial-loss prevention or national impact without evaluation evidence.

Two candidate pipelines are available. They never download data, approve a model, or
activate it automatically:

```powershell
# From backend/, using the project virtual environment executable:
python -m pip install -r requirements-ml.txt
python -m app.ml.train_message --csv ../datasets/authorized.csv --provenance ../datasets/provenance.json --output ../models/message-candidate
python -m app.ml.train_url --csv ../datasets/authorized-urls.csv --provenance ../datasets/url-provenance.json --output ../models/url-candidate
```

Message CSV: `text,label,language`. Labels 0 legitimate / 1 scam; languages en/ms. At least 200 normalized unique examples and 30 per language/label pair are needed for split feasibility, not sufficient for deployment validation. URL CSV: `url,label`, with labels 0 legitimate / 1 phishing, at least 200 unique URLs and 50 per label. Provenance must contain actual `source`, `license`, `permission_basis` and `labeling_method`. Private messages require authorization/de-identification; no data is downloaded implicitly.

Message experiments compare word TF-IDF + Naive Bayes, word/character TF-IDF + logistic regression, and calibrated word/character TF-IDF + linear SVM. URL experiments compare logistic regression and random forest over fixed lexical features. URL parsing is network-free: it performs no DNS lookup, fetch, or redirect. Selection uses held-out F1 with precision as the tie-breaker. Reports include precision, recall, F1, confusion matrix, false-positive/negative rates, Brier score, latency, hashes, and relevant language breakdowns.

Artifacts are `message_model.skops` or `url_model.skops` plus `evaluation.json`, with dataset/model SHA-256 hashes, split sizes and `validated:false`. Candidate training never automatically approves or activates a model. Safe loading requires a matching artifact hash, licensed provenance, reviewer, validation notes, `validated:true`, and an evidence-based `threshold_policy` containing `medium` and `high` values. No untrusted artifact types are automatically allowed; pickle/joblib is not loaded.

After independent review, configure absolute paths with `ML_MESSAGE_ARTIFACT`, `ML_MESSAGE_REPORT`, `ML_URL_ARTIFACT`, and `ML_URL_REPORT`. Both the web API and Telegram bot then use the same guarded runtime. An absent model stays on `explainable-rules-v1`; partial path configuration fails closed. `/api/v1/health` reports message and URL activation independently.

Required independent evaluation before activation:

- Audit near duplicates, related campaigns and source overlap; the included normalizer removes exact duplicates only. A source/campaign-grouped external test set is needed for generalization claims.
- Review labeling agreement, class/language balance, collection bias, false-positive/negative cases and adverse user consequences.
- Measure calibration outside training, choose risk thresholds based on that evidence, and present probability separately from the rule indicator score.
- Pilot OCR quality, unfamiliar language variants, code-switching, legitimate job/financial communications and evasive messages.
- Keep model artifacts read-only, pin dependencies, verify hashes and repeat tests when changing the model/version.

`datasets/samples.json` is fictional demonstration content and must never be used to validate model accuracy. The rules microbenchmark in docs/benchmark.json measures only speed on fictional input, not detection quality.
