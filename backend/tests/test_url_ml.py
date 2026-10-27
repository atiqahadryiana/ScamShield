import pytest
from app.ml.url_features import FEATURE_NAMES, extract_url_features
from app.ml.runtime import apply_prediction
from app.services.detection import analyze_url


def test_url_features_are_fixed_length_and_network_free(monkeypatch):
    monkeypatch.setattr('socket.getaddrinfo', lambda *args, **kwargs: pytest.fail('must not resolve URLs'))
    features = extract_url_features('http://secure-login.example/verify?id=123')
    assert len(features) == len(FEATURE_NAMES)
    assert features[FEATURE_NAMES.index('uses_http')] == 1
    assert features[FEATURE_NAMES.index('suspicious_word_count')] >= 2


def test_reviewed_prediction_policy_controls_risk():
    class StubModel:
        threshold_policy = {'medium': .3, 'high': .7}

        def probability(self, value):
            return .82

    result = apply_prediction(analyze_url('https://example.com'), StubModel(), 'https://example.com')
    assert result.risk == 'HIGH'
    assert result.score == 82
    assert result.model_probability == .82
    assert result.engine == 'validated-ml-with-rule-explanations-v1'
