"""Optional third-party URL reputation checks.

Only the fixed PhishTank API host is contacted. The submitted destination is
sent as form data and is never opened or followed by ScamShield.
"""
import httpx

from app.schemas.requests import Assessment, Indicator

PHISHTANK_ENDPOINT = 'https://checkurl.phishtank.com/checkurl/'


def _is_true(value: object) -> bool:
    return value is True or str(value).casefold() in {'true', 'yes', 'y', '1'}


def check_phishtank(assessment: Assessment, url: str, app_key: str, user_agent: str) -> Assessment:
    if not app_key:
        assessment.threat_intelligence = 'phishtank_not_configured'
        return assessment

    try:
        response = httpx.post(
            PHISHTANK_ENDPOINT,
            data={'url': url, 'format': 'json', 'app_key': app_key},
            headers={'User-Agent': user_agent},
            timeout=4.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        result = response.json().get('results', {})
    except (httpx.HTTPError, ValueError, AttributeError):
        assessment.threat_intelligence = 'phishtank_unavailable'
        return assessment

    if _is_true(result.get('in_database')) and _is_true(result.get('verified')) and _is_true(result.get('valid')):
        assessment.indicators.append(Indicator(
            id='phishtank_verified',
            weight=70,
            title='Verified phishing report in PhishTank',
            title_ms='Laporan pancingan data disahkan dalam PhishTank',
            explanation='PhishTank lists this exact URL as a verified, valid phishing page. Do not open it or submit any information.',
            explanation_ms='PhishTank menyenaraikan URL tepat ini sebagai halaman pancingan data yang sah dan disahkan. Jangan buka atau masukkan sebarang maklumat.',
        ))
        assessment.score = min(100, assessment.score + 70)
        assessment.risk = 'HIGH'
        assessment.category = 'phishing'
        assessment.threat_intelligence = 'phishtank_verified_phishing'
    elif _is_true(result.get('in_database')):
        assessment.threat_intelligence = 'phishtank_listed_unverified'
    else:
        # Absence from a community database is not evidence that a URL is safe.
        assessment.threat_intelligence = 'phishtank_no_match'
    return assessment
