# Dataset policy

No training dataset is bundled. `samples.json` is fictional demonstration/test content, not training or evaluation data. No trained or validated model is claimed.

For authorized data, provide UTF-8 CSV with `text,label,language` (label 0 legitimate / 1 scam; language en / ms). Do not commit private communications. Document consent, license, source, labeling, de-identification, campaign groups and permitted use in provenance JSON. Obtain independent labels and audit disagreement.

For authorized URL data, provide UTF-8 CSV with `url,label` (label 0 legitimate / 1 phishing). Treat URL strings as potentially sensitive and do not visit them during preparation. The trainer extracts lexical features locally and never performs DNS or HTTP requests.

The five public datasets documented by the project can be normalized with
`python scripts/prepare_public_datasets.py` after placing the original files under
`datasets/raw/`. Dataset-specific provenance and cleaning counts are written to
`datasets/processed/manifest.json`. See `ATTRIBUTION.md` for required credits.

Example provenance keys (fill with actual evidence, never invented claims): `source`, `license`, `permission_basis`, `labeling_method`. Supply a local file to the training CLI. Review exact and near duplicates, related campaigns, collection bias and source overlap before accepting a split. Use campaign/source-grouped independent evaluation for production.
