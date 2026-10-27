"""Lazy, optional runtime for independently reviewed model artifacts."""
from functools import lru_cache
from app.core.config import get_settings
from app.ml.inference import ValidatedModel, ValidatedURLModel


class ModelRuntime:
    def __init__(self):
        settings = get_settings()
        self.message = self._load(ValidatedModel, settings.ml_message_artifact, settings.ml_message_report)
        self.url = self._load(ValidatedURLModel, settings.ml_url_artifact, settings.ml_url_report)

    @staticmethod
    def _load(loader, artifact: str, report: str):
        if not artifact and not report:
            return None
        if not artifact or not report:
            raise ValueError('Both model artifact and reviewed report paths are required.')
        return loader(artifact, report)

    def status(self):
        return {'message': 'validated_active' if self.message else 'rules_only', 'url': 'validated_active' if self.url else 'rules_only'}


@lru_cache
def get_runtime() -> ModelRuntime:
    return ModelRuntime()


def apply_prediction(assessment, model, value):
    if model is None:
        return assessment
    probability = model.probability(value)
    policy = model.threshold_policy
    assessment.model_probability = probability
    assessment.score = round(probability * 100)
    assessment.score_type = 'validated_model_probability_percent'
    assessment.risk = 'HIGH' if probability >= policy['high'] else 'MEDIUM' if probability >= policy['medium'] else 'LOW'
    assessment.engine = 'validated-ml-with-rule-explanations-v1'
    return assessment
