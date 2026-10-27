"""Train and compare bilingual binary message-classification candidates."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

from app.ml.evaluation import binary_metrics, provenance
from app.ml.train import load_dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.feature_selection import SelectPercentile, chi2
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.svm import LinearSVC
    import skops.io as sio

    source = provenance(args.provenance)
    texts, labels, languages = load_dataset(args.csv)
    strata = [f'{label}-{language}' for label, language in zip(labels, languages)]
    counts = Counter(strata)
    if len(texts) < 200 or len(counts) != 4 or min(counts.values()) < 30:
        raise SystemExit('Supply at least 200 unique messages and 30 for each English/Malay label pair.')
    indices = list(range(len(texts)))
    train_idx, test_idx = train_test_split(indices, test_size=.2, random_state=42, stratify=strata)
    train_x = [texts[i] for i in train_idx]
    train_y = [labels[i] for i in train_idx]
    test_x = [texts[i] for i in test_idx]
    test_y = [labels[i] for i in test_idx]

    word = lambda: TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=30000)
    combined = lambda: FeatureUnion([
        ('word', word()),
        ('character', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True, min_df=2, max_features=30000)),
    ])
    candidates = {
        'word_naive_bayes': Pipeline([('features', word()), ('classifier', MultinomialNB())]),
        'word_character_logistic': Pipeline([('features', combined()), ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))]),
        'word_character_linear_svm': CalibratedClassifierCV(
            Pipeline([('features', combined()), ('select', SelectPercentile(chi2, percentile=80)), ('classifier', LinearSVC(class_weight='balanced', random_state=42))]),
            method='sigmoid', cv=3,
        ),
    }
    reports, fitted = {}, {}
    for name, model in candidates.items():
        model.fit(train_x, train_y)
        started = time.perf_counter()
        probabilities = model.predict_proba(test_x)[:, 1]
        latency = (time.perf_counter() - started) * 1000 / len(test_x)
        predictions = (probabilities >= .5).astype(int)
        reports[name] = {**binary_metrics(test_y, predictions, probabilities), 'mean_batch_latency_ms_per_message': latency}
        fitted[name] = model
    selected = max(reports, key=lambda name: (reports[name]['f1'], reports[name]['precision']))
    selected_predictions = (fitted[selected].predict_proba(test_x)[:, 1] >= .5).astype(int)
    language_reports = {}
    for language in ('en', 'ms'):
        positions = [j for j, i in enumerate(test_idx) if languages[i] == language]
        language_reports[language] = binary_metrics([test_y[j] for j in positions], [selected_predictions[j] for j in positions])

    args.output.mkdir(parents=True, exist_ok=True)
    artifact = args.output / 'message_model.skops'
    sio.dump(fitted[selected], artifact)
    report = {
        'validated': False, 'model_kind': 'message', 'status': 'candidate_requires_independent_review',
        'dataset_provenance': source, 'dataset_sha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        'unique_rows': len(texts), 'training_rows': len(train_idx), 'heldout_rows': len(test_idx),
        'experiments': reports, 'selected_model': selected, 'model_metrics': reports[selected],
        'languages': language_reports, 'threshold_policy': None,
        'limitations': ['Exact normalized duplicates are removed, but campaign variants require a grouped external evaluation.', 'Internal calibration does not establish real-world calibration.', 'Candidate training does not approve or activate a model.'],
    }
    report['model_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'selected_model': selected, 'model_metrics': reports[selected]}, indent=2))


if __name__ == '__main__':
    main()
