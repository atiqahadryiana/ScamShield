import httpx

from app.services.detection import analyze_url
from app.services.threat_intelligence import PHISHTANK_ENDPOINT, check_phishtank


def response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request('POST', PHISHTANK_ENDPOINT))


def test_verified_phishtank_match_is_high_risk(monkeypatch):
    monkeypatch.setattr('app.services.threat_intelligence.httpx.post', lambda *args, **kwargs: response({'results': {'in_database': True, 'verified': 'y', 'valid': 'y'}}))
    result = check_phishtank(analyze_url('https://example.test/login'), 'https://example.test/login', 'test-key', 'phishtank/scamshield-test')
    assert result.risk == 'HIGH'
    assert result.category == 'phishing'
    assert result.threat_intelligence == 'phishtank_verified_phishing'
    assert 'phishtank_verified' in {item.id for item in result.indicators}


def test_no_match_does_not_lower_local_result(monkeypatch):
    monkeypatch.setattr('app.services.threat_intelligence.httpx.post', lambda *args, **kwargs: response({'results': {'in_database': False}}))
    result = check_phishtank(analyze_url('https://bit.ly/example'), 'https://bit.ly/example', 'test-key', 'phishtank/scamshield-test')
    assert result.risk == 'MEDIUM'
    assert result.score == 30
    assert result.threat_intelligence == 'phishtank_no_match'


def test_unconfigured_phishtank_makes_no_request(monkeypatch):
    monkeypatch.setattr('app.services.threat_intelligence.httpx.post', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network call')))
    result = check_phishtank(analyze_url('https://example.test'), 'https://example.test', '', 'phishtank/scamshield-test')
    assert result.threat_intelligence == 'phishtank_not_configured'
