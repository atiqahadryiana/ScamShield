# Model artifacts

No trained model is included or active. Install `backend/requirements-ml.txt` to use the candidate TF-IDF/logistic regression training pipeline. Artifacts use skops, not pickle/joblib deserialization. The CLI outputs heldout metrics, per-language metrics, Brier score, rule comparison, dataset/artifact hashes and an explicit `validated: false` report.

`ValidatedModel` implements opt-in artifact loading after a separate review. Do not change a report to `validated: true` without evaluating calibration, false positives, false negatives, both languages, source/campaign leakage and external generalization. Provide actual reviewer and validation notes. Runtime model activation is intentionally not configured for the competition baseline; there is no approved dataset in this repository. Integrating a reviewed model into risk classification requires a documented threshold policy and additional API/Telegram consistency tests.
