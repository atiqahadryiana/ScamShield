import pytest
from app.services.detection import analyze_text, analyze_url


@pytest.mark.parametrize('text', [
    'Congratulations! You have been selected for a part-time job earning RM500 daily. Pay RM50 registration fee immediately to secure your position.',
    'Anda telah memenangi hadiah RM10,000! Klik pautan ini dan bayar RM100 untuk menuntut hadiah.',
])
def test_suspicious_examples(text):
    result = analyze_text(text)
    assert result.risk == 'HIGH'
    assert result.model_probability is None
    assert result.score_type == 'heuristic_indicator_score'
    assert len(result.indicators) >= 3


def test_benign_and_negative_credential_context():
    assert analyze_text('Hello, our project meeting is at 10 today.').risk == 'LOW'
    assert 'credentials' not in {i.id for i in analyze_text('Never share your OTP.').indicators}


def test_unicode_obfuscation():
    result = analyze_text('Ｃｏｎｇｒａｔｕｌａｔｉｏｎｓ! Pay RM50 registration fee imme\u200bdiately.')
    assert result.risk == 'HIGH'


@pytest.mark.parametrize('url,flag', [
    ('http://127.0.0.1/login', 'private_address'),
    ('https://maybank.verify.example.com/login', 'brand_domain'),
    ('https://maybank2u.com.my@evil.example/login', 'userinfo'),
    ('https://xn--pple-43d.example', 'unicode_domain'),
    ('https://bit.ly/demo', 'shortener'),
    ('https://example.com/?next=https://other.example', 'redirect_parameter'),
])
def test_url_features(url, flag):
    assert flag in {i.id for i in analyze_url(url).indicators}


@pytest.mark.parametrize('url', ['file:///etc/passwd', 'javascript:alert(1)', 'https://', 'https://example.com:bad', 'https://a..example.com'])
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        analyze_url(url)


def test_no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('URL scanner must never access the network')
    monkeypatch.setattr('socket.getaddrinfo', fail)
    result = analyze_url('https://www.bnm.gov.my/')
    assert result.risk == 'LOW'
    assert result.threat_intelligence == 'not_configured'
