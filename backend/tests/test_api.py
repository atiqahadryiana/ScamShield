import io
from datetime import timedelta
from PIL import Image
from app.core.database import get_db
from app.main import app
from app.models.entities import User, ScanRecord, now
from app.services.ocr import OCRUnavailable
from app.main import same_origin
from starlette.requests import Request


def account(client, email='reader@example.test'):
    result = client.post('/api/v1/auth/register', json={'email': email, 'password': 'long-test-password'})
    assert result.status_code == 201
    return result.json()


def test_text_api_privacy_and_validation(client):
    response = client.post('/api/v1/scan/text', json={'text': 'Pay RM50 registration fee immediately. Congratulations!'})
    assert response.status_code == 200
    assert response.json()['risk'] == 'HIGH'
    assert client.get('/api/v1/dashboard/summary').json()['total_scans'] == 1
    assert client.get('/api/v1/scan/' + response.json()['id']).status_code == 401
    invalid = client.post('/api/v1/scan/text', json={'text': 'x' * 10001})
    assert invalid.status_code == 422
    assert 'x' * 100 not in invalid.text
    assert client.post('/api/v1/scan/text', json={'text': '   '}).status_code == 422
    assert client.post('/api/v1/scan/text', json={'text': 'hello', 'save_history': True}).status_code == 401


def test_history_ownership_expiry_and_deletion(client):
    account(client)
    assert client.put('/api/v1/auth/preferences', json={'dashboard_days': 7}).json()['preferences']['dashboard_days'] == 7
    assert client.put('/api/v1/auth/preferences', json={'dashboard_days': 9}).status_code == 422
    result = client.post('/api/v1/scan/text', json={'text': 'Hello, meeting today.', 'save_history': True}).json()
    assert client.get('/api/v1/scan/' + result['id']).status_code == 200
    assert len(client.get('/api/v1/history').json()) == 1
    client.post('/api/v1/auth/logout')
    account(client, 'other@example.test')
    assert client.get('/api/v1/scan/' + result['id']).status_code == 404
    assert client.get('/api/v1/history').json() == []
    assert client.get('/api/v1/admin/overview').status_code == 403
    client.post('/api/v1/auth/logout')
    client.post('/api/v1/auth/login', json={'email': 'reader@example.test', 'password': 'long-test-password'})
    client.delete('/api/v1/history')
    assert client.get('/api/v1/history').json() == []


def test_csrf_and_rate_limit(client):
    assert client.post('/api/v1/scan/text', json={'text': 'hello'}, headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert client.post('/api/v1/scan/text', json={'text': 'hello'}, headers={'X-ScamShield-Client': ''}).status_code == 403
    codes = [client.post('/api/v1/scan/text', json={'text': 'hello'}).status_code for _ in range(31)]
    assert 429 in codes


def test_same_origin_supports_dynamic_deployment_hosts():
    scope = {'type': 'http', 'method': 'POST', 'path': '/', 'headers': [(b'host', b'preview.example.test')]}
    request = Request(scope)
    assert same_origin(request, 'https://preview.example.test') is True
    assert same_origin(request, 'https://attacker.example.test') is False
    proxied = Request({'type': 'http', 'method': 'POST', 'path': '/', 'client': ('::1', 3000), 'headers': [(b'host', b'internal.test'), (b'x-forwarded-host', b'preview.example.test')]})
    assert same_origin(proxied, 'https://preview.example.test') is True
    untrusted = Request({'type': 'http', 'method': 'POST', 'path': '/', 'client': ('203.0.113.2', 3000), 'headers': [(b'host', b'internal.test'), (b'x-forwarded-host', b'preview.example.test')]})
    assert same_origin(untrusted, 'https://preview.example.test') is False


def test_url_and_resources(client):
    assert client.post('/api/v1/scan/url', json={'url': 'http://127.0.0.1/a'}).json()['risk'] == 'HIGH'
    assert client.post('/api/v1/scan/url', json={'url': 'file:///secret'}).status_code == 422
    assert client.get('/api/v1/resources').json()['integration'] == 'official_links_only'


def test_quiz_server_side_grading(client):
    modules = client.get('/api/v1/education/modules').json()
    assert len(modules) == 8
    assert 'correct' not in modules[0]['questions'][0]
    result = client.post('/api/v1/education/quiz', json={'module_id': 'phishing', 'answers': [1], 'stage': 'pre'})
    assert result.json()['score'] == 1
    assert client.post('/api/v1/education/quiz', json={'module_id': 'phishing', 'answers': [99]}).status_code == 422
    assert client.get('/api/v1/dashboard/summary').json()['quiz_attempts'] == 1


def test_ocr_review_and_fallback(client, monkeypatch):
    output = io.BytesIO()
    Image.new('RGB', (100, 100), 'white').save(output, format='PNG')
    monkeypatch.setattr('app.services.ocr.pytesseract.image_to_string', lambda *a, **k: 'Review this extracted text')
    result = client.post('/api/v1/scan/image', files={'file': ('screen.png', output.getvalue(), 'image/png')})
    assert result.status_code == 200
    assert result.json()['requires_review'] is True
    assert client.get('/api/v1/dashboard/summary').json()['total_scans'] == 0
    assert client.post('/api/v1/scan/image', files={'file': ('bad.png', b'not an image', 'image/png')}).status_code == 422
    assert client.post('/api/v1/scan/image', files={'file': ('bad.svg', b'<svg/>', 'image/svg+xml')}).status_code == 422


def test_oversized_request_and_ocr_failure(client, monkeypatch):
    response = client.post('/api/v1/scan/text', content=b'x' * (6 * 1024 * 1024 + 1), headers={'Content-Type': 'application/json'})
    assert response.status_code == 413
    def unavailable(*args, **kwargs):
        raise OCRUnavailable('Install Tesseract or paste the text.')
    monkeypatch.setattr('app.api.routes.extract_text', unavailable)
    assert client.post('/api/v1/scan/image', files={'file': ('file.png', b'image', 'image/png')}).status_code == 503


def test_expired_history_is_hidden_and_cleanup_deletes(client):
    account(client)
    assessment = client.post('/api/v1/scan/text', json={'text': 'A fictional meeting today.', 'save_history': True}).json()
    factory = app.dependency_overrides[get_db]
    with next(factory()) as db:
        row = db.get(ScanRecord, assessment['id'])
        row.created_at = now() - timedelta(days=31)
        db.commit()
    assert client.get('/api/v1/scan/' + assessment['id']).status_code == 404
    assert client.get('/api/v1/history').json() == []
    from app.services.storage import cleanup
    with next(factory()) as db:
        assert cleanup(db)['expired_scans_deleted'] == 1
        assert db.get(ScanRecord, assessment['id']) is None


def test_account_delete_revokes_session_and_cascades(client):
    account(client)
    client.post('/api/v1/scan/text', json={'text': 'A fictional meeting today.', 'save_history': True})
    assert client.delete('/api/v1/auth/account').status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 401
    from sqlalchemy import func, select
    with next(app.dependency_overrides[get_db]()) as db:
        assert db.scalar(select(func.count(ScanRecord.id))) == 0


def test_admin_authorization_and_audit(client):
    account(client)
    assert client.post('/api/v1/admin/notices', json={'title': 'Test notice', 'body': 'Community safety notice'}).status_code == 403
    factory = app.dependency_overrides[get_db]
    db = next(factory())
    from sqlalchemy import select
    user = db.scalar(select(User).where(User.email == 'reader@example.test'))
    user.role = 'admin'
    db.commit()
    db.close()
    created = client.post('/api/v1/admin/notices', json={'title': 'Test notice', 'body': 'Community safety notice'})
    assert created.status_code == 201
    assert client.get('/api/v1/admin/overview').json()['audit'][0]['action'] == 'notice_created'
