"""Opt-in safe artifact inference, gated by a separately reviewed validation report.
The default application remains rules-only until an authorized dataset is evaluated.
"""
import hashlib
import json
from pathlib import Path


def _reviewed_report(artifact: Path, report_path: str, kind: str) -> dict:
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    if report.get('validated') is not True or not report.get('reviewer') or not report.get('validation_notes'):
        raise ValueError('A human-reviewed validation report is required before model activation.')
    if report.get('model_kind', kind) != kind:
        raise ValueError(f'Expected a reviewed {kind} model report.')
    if report.get('model_sha256') != hashlib.sha256(artifact.read_bytes()).hexdigest():
        raise ValueError('Model does not match the reviewed artifact hash.')
    policy = report.get('threshold_policy') or {}
    medium, high = policy.get('medium'), policy.get('high')
    if not isinstance(medium, (int, float)) or not isinstance(high, (int, float)) or not 0 <= medium < high <= 1:
        raise ValueError('Reviewed threshold_policy must define 0 <= medium < high <= 1.')
    return report


class ValidatedModel:
    def __init__(self, artifact_path: str, report_path: str):
        import skops.io as sio
        artifact = Path(artifact_path)
        if artifact.stat().st_size > 100 * 1024 * 1024:
            raise ValueError('Model exceeds the 100 MB limit.')
        report = _reviewed_report(artifact, report_path, 'message')
        if set(report.get('languages', {})) != {'en', 'ms'} or not report.get('dataset_provenance', {}).get('license'):
            raise ValueError('Both languages and licensed dataset provenance must be evaluated.')
        unknown = sio.get_untrusted_types(file=artifact)
        if unknown:
            raise ValueError('Artifact contains types outside the default safe skops allowlist. Review it offline; arbitrary types are never auto-trusted.')
        self.model = sio.load(artifact, trusted=[])
        if list(self.model.classes_) != [0, 1]:
            raise ValueError('Classifier classes must be 0 legitimate and 1 scam.')
        self.threshold_policy = report['threshold_policy']

    def probability(self, text: str) -> float:
        return float(self.model.predict_proba([text])[0, 1])


class ValidatedURLModel:
    def __init__(self, artifact_path: str, report_path: str):
        import skops.io as sio
        from app.ml.url_features import FEATURE_NAMES

        artifact = Path(artifact_path)
        if artifact.stat().st_size > 100 * 1024 * 1024:
            raise ValueError('Model exceeds the 100 MB limit.')
        report = _reviewed_report(artifact, report_path, 'url')
        if report.get('feature_names') != FEATURE_NAMES or not report.get('dataset_provenance', {}).get('license'):
            raise ValueError('URL feature schema and licensed provenance must match the reviewed report.')
        unknown = sio.get_untrusted_types(file=artifact)
        if unknown:
            raise ValueError('Artifact contains types outside the default safe skops allowlist.')
        self.model = sio.load(artifact, trusted=[])
        if list(self.model.classes_) != [0, 1]:
            raise ValueError('Classifier classes must be 0 legitimate and 1 phishing.')
        self.threshold_policy = report['threshold_policy']

    def probability(self, url: str) -> float:
        from app.ml.url_features import extract_url_features
        return float(self.model.predict_proba([extract_url_features(url)])[0, 1])
