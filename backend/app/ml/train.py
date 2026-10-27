"""Candidate model preparation, never automatic validation or activation.
python -m app.ml.train --csv ../datasets/authorized.csv --provenance ../datasets/provenance.json --output ../models/candidate
"""
import argparse
import csv
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path


def normalized(text: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text).casefold()).strip()


def load_dataset(path: Path) -> tuple[list[str], list[int], list[str]]:
    deduplicated = {}
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not {'text', 'label', 'language'} <= set(reader.fieldnames or []):
            raise ValueError('CSV requires text,label,language columns. Labels: 0 legitimate, 1 scam. Languages: en, ms.')
        for row in reader:
            text = normalized(row['text'])
            label = int(row['label'])
            language = row['language'].strip()
            if not 3 <= len(text) <= 10000 or label not in (0, 1) or language not in ('en', 'ms'):
                raise ValueError('Invalid text, label or language in dataset.')
            if text in deduplicated and deduplicated[text][0] != label:
                raise ValueError('Conflicting labels for normalized duplicate text.')
            deduplicated[text] = (label, language)
    return list(deduplicated), [x[0] for x in deduplicated.values()], [x[1] for x in deduplicated.values()]


def evaluate(truth, predictions) -> dict:
    from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score
    tn, fp, fn, tp = confusion_matrix(truth, predictions, labels=[0, 1]).ravel()
    return {'precision': float(precision_score(truth, predictions, zero_division=0)), 'recall': float(recall_score(truth, predictions, zero_division=0)), 'f1': float(f1_score(truth, predictions, zero_division=0)), 'confusion_matrix': [[int(tn), int(fp)], [int(fn), int(tp)]], 'false_positive_rate': float(fp / max(1, fp + tn)), 'false_negative_rate': float(fn / max(1, fn + tp))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--provenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    provenance = json.loads(args.provenance.read_text(encoding='utf-8'))
    if not all(provenance.get(k) for k in ('source', 'license', 'permission_basis', 'labeling_method')):
        raise SystemExit('Provenance must document source, license, permission_basis and labeling_method.')
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import brier_score_loss
    import skops.io as sio
    from app.services.detection import analyze_text

    texts, labels, languages = load_dataset(args.csv)
    strata = [f'{label}-{language}' for label, language in zip(labels, languages)]
    from collections import Counter
    counts = Counter(strata)
    if len(texts) < 200 or len(counts) != 4 or min(counts.values()) < 30:
        raise SystemExit('Supply at least 200 unique labeled messages, at least 30 for each language/label pair. This minimum enables splitting; it does not establish validation.')
    indices = list(range(len(texts)))
    train_idx, test_idx = train_test_split(indices, test_size=.2, random_state=42, stratify=strata)
    pipeline = Pipeline([('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=30000)), ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42))])
    # Calibration folds fit TF-IDF only on each training fold, avoiding vocabulary leakage.
    model = CalibratedClassifierCV(pipeline, method='sigmoid', cv=3)
    model.fit([texts[i] for i in train_idx], [labels[i] for i in train_idx])
    test_text = [texts[i] for i in test_idx]
    truth = [labels[i] for i in test_idx]
    started = time.perf_counter()
    probabilities = model.predict_proba(test_text)[:, 1]
    latency = (time.perf_counter() - started) * 1000 / len(test_idx)
    predictions = (probabilities >= .5).astype(int)
    report = {'validated': False, 'status': 'candidate_requires_independent_review', 'dataset_provenance': provenance, 'dataset_sha256': hashlib.sha256(args.csv.read_bytes()).hexdigest(), 'unique_rows': len(texts), 'training_rows': len(train_idx), 'heldout_rows': len(test_idx), 'model_metrics': evaluate(truth, predictions), 'brier_score': float(brier_score_loss(truth, probabilities)), 'mean_batch_inference_latency_ms_per_message': latency, 'rule_metrics': evaluate(truth, [int(analyze_text(text).risk == 'HIGH') for text in test_text]), 'languages': {}, 'limitations': ['Deduplication removes normalized exact duplicates, not paraphrases or related campaign templates. Audit campaign/source groups before a deployment evaluation.', 'A stratified heldout split and internal calibration do not establish real-world calibration or fairness.', 'Rule comparison treats HIGH as positive; MEDIUM as negative. Threshold choices affect metrics.', 'No authorized dataset was bundled with this repository. Synthetic test fixtures must never serve as a validation dataset.']}
    for language in ('en', 'ms'):
        selected = [j for j, i in enumerate(test_idx) if languages[i] == language]
        report['languages'][language] = evaluate([truth[j] for j in selected], [predictions[j] for j in selected])
    args.output.mkdir(parents=True, exist_ok=True)
    artifact = args.output / 'model.skops'
    sio.dump(model, artifact)
    report['model_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'unique_rows', 'heldout_rows', 'model_metrics', 'brier_score')}, indent=2))


if __name__ == '__main__':
    main()
