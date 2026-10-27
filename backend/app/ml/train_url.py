"""Train and compare network-free phishing URL candidate models."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from app.ml.evaluation import binary_metrics, provenance
from app.ml.url_features import FEATURE_NAMES, extract_many, parse_url


def load_url_dataset(path: Path):
    rows = {}
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not {'url', 'label'} <= set(reader.fieldnames or []):
            raise ValueError('CSV requires url,label columns with labels 0 legitimate and 1 phishing.')
        for row in reader:
            raw, _, _ = parse_url(row['url'])
            label = int(row['label'])
            if label not in (0, 1):
                raise ValueError('URL labels must be 0 legitimate or 1 phishing.')
            key = raw.casefold()
            if key in rows and rows[key] != label:
                raise ValueError('Conflicting labels for duplicate URL.')
            rows[key] = label
    return list(rows), list(rows.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    import skops.io as sio

    source = provenance(args.provenance)
    urls, labels = load_url_dataset(args.csv)
    counts = Counter(labels)
    if len(urls) < 200 or min(counts.values(), default=0) < 50:
        raise SystemExit('Supply at least 200 unique URLs and 50 examples per label.')
    train_urls, test_urls, train_y, test_y = train_test_split(urls, labels, test_size=.2, random_state=42, stratify=labels)
    train_x, test_x = extract_many(train_urls), extract_many(test_urls)
    candidates = {
        'logistic_regression': LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42),
        'random_forest': RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=-1),
    }
    reports = {}
    fitted = {}
    for name, model in candidates.items():
        model.fit(train_x, train_y)
        started = time.perf_counter()
        probabilities = model.predict_proba(test_x)[:, 1]
        latency = (time.perf_counter() - started) * 1000 / len(test_x)
        predictions = (probabilities >= .5).astype(int)
        reports[name] = {**binary_metrics(test_y, predictions, probabilities), 'mean_batch_latency_ms_per_url': latency}
        fitted[name] = model
    selected = max(reports, key=lambda name: (reports[name]['f1'], reports[name]['precision']))
    args.output.mkdir(parents=True, exist_ok=True)
    artifact = args.output / 'url_model.skops'
    sio.dump(fitted[selected], artifact)
    report = {
        'validated': False, 'model_kind': 'url', 'status': 'candidate_requires_independent_review',
        'dataset_provenance': source, 'dataset_sha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        'unique_rows': len(urls), 'training_rows': len(train_urls), 'heldout_rows': len(test_urls),
        'feature_names': FEATURE_NAMES, 'experiments': reports, 'selected_model': selected,
        'model_metrics': reports[selected], 'threshold_policy': None,
        'limitations': ['Lexical features do not establish whether a site is malicious.', 'No URL is fetched, resolved, or checked against live threat intelligence.', 'Use a domain/campaign-grouped external test before deployment.'],
    }
    report['model_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'selected_model': selected, 'model_metrics': reports[selected]}, indent=2))


if __name__ == '__main__':
    main()
