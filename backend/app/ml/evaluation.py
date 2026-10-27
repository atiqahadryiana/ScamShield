"""Evaluation helpers shared by candidate training commands."""
from __future__ import annotations


def binary_metrics(truth, predictions, probabilities=None) -> dict:
    from sklearn.metrics import brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score

    tn, fp, fn, tp = confusion_matrix(truth, predictions, labels=[0, 1]).ravel()
    output = {
        'precision': float(precision_score(truth, predictions, zero_division=0)),
        'recall': float(recall_score(truth, predictions, zero_division=0)),
        'f1': float(f1_score(truth, predictions, zero_division=0)),
        'confusion_matrix': [[int(tn), int(fp)], [int(fn), int(tp)]],
        'false_positive_rate': float(fp / max(1, fp + tn)),
        'false_negative_rate': float(fn / max(1, fn + tp)),
    }
    if probabilities is not None:
        output['brier_score'] = float(brier_score_loss(truth, probabilities))
    return output


def provenance(path) -> dict:
    import json

    value = json.loads(path.read_text(encoding='utf-8'))
    required = ('source', 'license', 'permission_basis', 'labeling_method')
    if not all(value.get(key) for key in required):
        raise ValueError('Provenance must document source, license, permission_basis and labeling_method.')
    return value
