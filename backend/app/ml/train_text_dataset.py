"""Train comparable text classifiers while preserving each dataset's labels."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from app.ml.preprocess import normalize_text


def load(path: Path):
    grouped = defaultdict(set)
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not {'text', 'label'} <= set(reader.fieldnames or []):
            raise ValueError('CSV requires text,label columns.')
        for row in reader:
            text, label = normalize_text(row['text']), row['label'].strip().casefold()
            if text and label:
                grouped[text].add(label)
    conflicting = [text for text, labels in grouped.items() if len(labels) > 1]
    if conflicting:
        raise ValueError('Conflicting labels remain after normalization.')
    return list(grouped), [next(iter(labels)) for labels in grouped.values()]


def metrics(truth, predicted, labels):
    from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
    precision, recall, f1, support = precision_recall_fscore_support(truth, predicted, labels=labels, zero_division=0)
    return {
        'macro_precision': float(sum(precision) / len(precision)),
        'macro_recall': float(sum(recall) / len(recall)),
        'macro_f1': float(sum(f1) / len(f1)),
        'classes': {label: {'precision': float(precision[i]), 'recall': float(recall[i]), 'f1': float(f1[i]), 'support': int(support[i])} for i, label in enumerate(labels)},
        'confusion_matrix': confusion_matrix(truth, predicted, labels=labels).astype(int).tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.svm import LinearSVC
    import skops.io as sio

    provenance = json.loads(args.provenance.read_text(encoding='utf-8'))
    if not all(provenance.get(key) for key in ('source', 'license', 'permission_basis', 'labeling_method')):
        raise ValueError('Incomplete provenance.')
    texts, labels = load(args.csv)
    counts = Counter(labels)
    if len(texts) < 100 or len(counts) < 2 or min(counts.values()) < 20:
        raise ValueError('Need at least 100 unique rows, two classes, and 20 rows per class.')
    train_x, test_x, train_y, test_y = train_test_split(texts, labels, test_size=.2, random_state=42, stratify=labels)
    word = lambda: TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=40000)
    combined = lambda: FeatureUnion([('word', word()), ('character', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, sublinear_tf=True, max_features=40000))])
    candidates = {
        'word_naive_bayes': Pipeline([('features', word()), ('classifier', MultinomialNB())]),
        'word_character_logistic': Pipeline([('features', combined()), ('classifier', LogisticRegression(max_iter=1500, class_weight='balanced', random_state=42))]),
        'word_character_linear_svm': Pipeline([('features', combined()), ('classifier', LinearSVC(class_weight='balanced', random_state=42))]),
    }
    reports, fitted = {}, {}
    ordered_labels = sorted(counts)
    for name, model in candidates.items():
        model.fit(train_x, train_y)
        started = time.perf_counter()
        predicted = model.predict(test_x)
        latency = (time.perf_counter() - started) * 1000 / len(test_x)
        reports[name] = {**metrics(test_y, predicted, ordered_labels), 'mean_batch_latency_ms_per_message': latency}
        fitted[name] = model
    selected = max(reports, key=lambda name: reports[name]['macro_f1'])
    args.output.mkdir(parents=True, exist_ok=True)
    artifact = args.output / 'text_model.skops'
    sio.dump(fitted[selected], artifact)
    report = {
        'validated': False, 'model_kind': 'dataset_specific_text', 'status': 'research_candidate_not_for_runtime',
        'dataset_provenance': provenance, 'dataset_sha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        'unique_rows': len(texts), 'class_distribution': dict(counts), 'training_rows': len(train_x), 'heldout_rows': len(test_x),
        'labels': ordered_labels, 'experiments': reports, 'selected_model': selected, 'model_metrics': reports[selected],
        'limitations': ['Random stratified splitting does not prevent campaign or source leakage.', 'Dataset-specific labels are not interchangeable.', 'This artifact is not approved for live runtime activation.'],
    }
    report['model_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'dataset': provenance['source'], 'selected_model': selected, 'metrics': reports[selected]}, indent=2))


if __name__ == '__main__':
    main()
