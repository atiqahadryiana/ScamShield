"""Shared deterministic analysis. Scores are indicator weights, never probabilities.
URL analysis is lexical only: no DNS lookup, HTTP request, redirects, or execution.
"""
import ipaddress
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote
from uuid import uuid4
from app.schemas.requests import Assessment, Indicator

RULES = [
    ('upfront_fee', r'(registration fee|upfront|processing fee|activation fee|deposit keselamatan|yuran pendaftaran|bayar\s+rm|pay\s+rm|bayaran pendahuluan|bayar dahulu)', 32, 'Upfront payment request', 'Permintaan bayaran pendahuluan', 'A request to pay before receiving a job, reward or service deserves independent verification.', 'Permintaan bayaran sebelum menerima kerja, hadiah atau perkhidmatan perlu disahkan.'),
    ('reward', r'(congratulations|you (?:have )?won|selected for|memenangi|tahniah|menuntut hadiah|claim.{0,20}prize|hadiah\s+rm)', 24, 'Unexpected reward or selection', 'Hadiah atau pemilihan tidak dijangka', 'Unexpected prizes and unsolicited selections are common scam hooks.', 'Hadiah atau pemilihan tanpa diminta boleh menjadi umpan penipuan.'),
    ('urgency', r'(immediately|urgent|act now|within \d+ hours|segera|sekarang|limited time|secure your position|last chance|akan disekat|account.{0,20}(suspended|blocked))', 20, 'Pressure to act quickly', 'Tekanan untuk bertindak segera', 'Time pressure can discourage checking the sender independently.', 'Tekanan masa boleh menghalang pengesahan pengirim secara bebas.'),
    ('income', r'(rm\s*\d[\d,]*\s*(daily|sehari)|earn.{0,20}(daily|a day)|guaranteed.{0,20}(profit|return)|pulangan dijamin|tanpa risiko|risk.free|keuntungan.{0,20}dijamin)', 28, 'Unrealistic earnings or guaranteed returns', 'Pendapatan luar biasa atau pulangan dijamin', 'High daily income or guaranteed investment returns warrant extra scrutiny.', 'Pendapatan harian tinggi atau pulangan dijamin perlu diperiksa dengan teliti.'),
    ('credentials', r'((share|send|provide|enter|verify|confirm|hantar|berikan|masukkan|kongsi).{0,45}(otp|tac|password|pin|kata laluan|recovery code)|(?:otp|tac|password|kata laluan).{0,30}(required|diperlukan))', 48, 'Request for sensitive credentials', 'Permintaan maklumat rahsia', 'Never share banking passwords, OTPs, TACs or recovery codes with a message sender.', 'Jangan kongsi kata laluan bank, OTP, TAC atau kod pemulihan.'),
    ('impersonation', r'(bank negara|lhdn|pdrm|royal malaysia police|kastam|maybank|cimb|pos malaysia|government|pegawai polis|mahkamah)', 10, 'Authority or brand claim', 'Dakwaan pihak berkuasa atau jenama', 'A brand or authority name alone does not establish the sender’s identity.', 'Nama jenama atau pihak berkuasa tidak membuktikan identiti pengirim.'),
    ('external_link', r'(https?://|klik pautan|click.{0,12}link)', 10, 'External link or click request', 'Pautan luar atau permintaan klik', 'Open the organization’s official site independently rather than following an unsolicited link.', 'Buka laman rasmi organisasi secara bebas daripada pautan dalam mesej.'),
    ('recruitment', r'(part.time|kerja sambilan|job offer|tawaran kerja|recruitment|hiring)', 10, 'Unsolicited recruitment language', 'Bahasa pengambilan pekerja', 'Verify the employer and recruiter before sharing documents or paying any fees.', 'Sahkan majikan dan perekrut sebelum berkongsi dokumen atau membayar yuran.'),
    ('investment', r'(investment|pelaburan|crypto|forex|saham)', 8, 'Investment solicitation', 'Tawaran pelaburan', 'Check the provider’s authorization through relevant official regulators.', 'Semak kebenaran penyedia melalui pengawal selia rasmi.'),
]

DISCLAIMER = 'Automated assessment cannot conclusively determine fraud. Low risk does not mean guaranteed safe. This score measures detected indicators, not the probability of a scam.'
DISCLAIMER_MS = 'Penilaian automatik tidak dapat mengesahkan penipuan secara muktamad. Risiko rendah tidak menjamin keselamatan. Skor ini mengukur petunjuk, bukan kebarangkalian penipuan.'


def indicator(key: str, weight: int, title: str, ms: str, why: str, why_ms: str) -> Indicator:
    return Indicator(id=key, weight=weight, title=title, title_ms=ms, explanation=why, explanation_ms=why_ms)


def result(indicators: list[Indicator], language: str, category: str, domain: str | None = None) -> Assessment:
    score = min(100, sum(i.weight for i in indicators))
    risk = 'HIGH' if score >= 60 else 'MEDIUM' if score >= 25 else 'LOW'
    return Assessment(id=str(uuid4()), risk=risk, score=score, language=language, category=category, indicators=indicators,
        recommendations=['Pause before paying or sharing personal information.', 'Verify the sender using independently obtained official contact details.', 'If money was transferred, contact your bank immediately and NSRC 997.'],
        recommendations_ms=['Berhenti sebelum membayar atau berkongsi maklumat peribadi.', 'Sahkan pengirim menggunakan maklumat hubungan rasmi yang diperoleh secara bebas.', 'Jika wang telah dipindahkan, hubungi bank anda segera dan NSRC 997.'],
        disclaimer=DISCLAIMER, disclaimer_ms=DISCLAIMER_MS, created_at=datetime.now(timezone.utc).isoformat(), domain=domain)


def analyze_text(text: str) -> Assessment:
    normalized = unicodedata.normalize('NFKC', text).casefold()
    normalized = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]', '', normalized)
    flags = []
    for key, pattern, weight, title, ms, why, why_ms in RULES:
        matches = list(re.finditer(pattern, normalized))
        if key == 'credentials':
            # Recognize common safety advice; retain positive requests in later clauses.
            matches = [m for m in matches if not re.search(r'(never|do not|don.t|jangan|tidak boleh)\s*$', normalized[max(0, m.start() - 20):m.start()])]
        if matches:
            flags.append(indicator(key, weight, title, ms, why, why_ms))
    keys = {i.id for i in flags}
    # Lexical URL indicators from embedded links use the identical URL analyzer.
    for match in re.findall(r'https?://[^\s<>]+', normalized)[:10]:
        try:
            for flag in analyze_url(match.rstrip('.,!?)')).indicators:
                if flag.id not in keys:
                    flags.append(flag)
                    keys.add(flag.id)
        except ValueError:
            pass
    language = 'ms' if re.search(r'\b(anda|telah|bayar|hadiah|pautan|segera|kerja|tahniah|pelaburan|untuk)\b', normalized) else 'en' if re.search(r'\b(the|you|have|your|please|for|hello|pay|meeting|today)\b', normalized) else 'und'
    category = 'job' if 'recruitment' in keys else 'investment' if 'investment' in keys else 'prize' if 'reward' in keys else 'impersonation' if 'impersonation' in keys else 'phishing' if 'credentials' in keys or 'external_link' in keys else 'other'
    return result(flags, language, category)


def analyze_url(raw: str) -> Assessment:
    raw = raw.strip()
    if len(raw) > 2048 or re.search(r'[\s\x00-\x1f\\]', raw):
        raise ValueError('Enter a valid HTTP or HTTPS URL without spaces or control characters.')
    parsed = urlsplit(raw if '://' in raw else 'https://' + raw)
    try:
        host = parsed.hostname or ''
        _ = parsed.port
        ascii_host = host.encode('idna').decode('ascii').lower()
    except (ValueError, UnicodeError):
        raise ValueError('The URL contains an invalid domain or port.') from None
    if parsed.scheme not in ('http', 'https') or not host or '.' not in host and ':' not in host or len(host) > 253:
        raise ValueError('Enter an HTTP or HTTPS URL with a valid domain.')
    flags: list[Indicator] = []

    def add(k: str, w: int, en: str, ms: str, why: str):
        flags.append(indicator(k, w, en, ms, why, 'Semak alamat laman secara bebas sebelum meneruskan.'))

    try:
        ip = ipaddress.ip_address(host)
        add('ip_domain', 30, 'IP address instead of a domain', 'Alamat IP menggantikan domain', 'Raw IP addresses hide the identity of the organization.')
        if not ip.is_global:
            add('private_address', 50, 'Private or local destination', 'Destinasi peribadi atau tempatan', 'This address points to a non-public network. It will never be fetched by this scanner.')
    except ValueError:
        if ascii_host.endswith(('.local', '.localhost', '.internal')) or ascii_host == 'localhost':
            add('private_address', 50, 'Local network hostname', 'Nama hos rangkaian tempatan', 'This is not a public organization domain.')
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', ascii_host) or '..' in ascii_host:
            raise ValueError('Invalid domain format.')
    if parsed.username is not None:
        add('userinfo', 35, 'Misleading address before @', 'Alamat mengelirukan sebelum @', 'The actual host comes after the @ sign; preceding text can imitate a trusted site.')
    if 'xn--' in ascii_host or any(ord(c) > 127 for c in host):
        add('unicode_domain', 25, 'Internationalized domain', 'Domain antarabangsa', 'Unicode or punycode domains may be legitimate, but can also imitate familiar letters.')
    if parsed.scheme == 'http':
        add('no_https', 15, 'Unencrypted HTTP address', 'Alamat HTTP tidak disulitkan', 'HTTP does not provide encrypted transport. HTTPS alone does not prove legitimacy either.')
    if len(raw) > 160:
        add('long_url', 15, 'Unusually long URL', 'URL terlalu panjang', 'Long addresses can obscure the destination or hide parameters.')
    if ascii_host.count('.') >= 4:
        add('subdomains', 20, 'Many nested subdomains', 'Banyak subdomain bersarang', 'Read the entire host; trusted names on the left may belong to an unrelated domain.')
    brands = {'maybank': 'maybank2u.com.my', 'cimb': 'cimb.com.my', 'bnm': 'bnm.gov.my', 'lhdn': 'hasil.gov.my', 'paypal': 'paypal.com'}
    if any(brand in ascii_host and not (ascii_host == official or ascii_host.endswith('.' + official)) for brand, official in brands.items()):
        add('brand_domain', 35, 'Brand name on an unrelated domain', 'Nama jenama pada domain lain', 'A familiar brand appears in a domain outside its recognized official domain. Check independently; this is a heuristic.')
    if ascii_host in {'bit.ly', 'tinyurl.com', 't.co', 'shorturl.at'}:
        add('shortener', 20, 'Shortened link conceals destination', 'Pautan pendek menyembunyikan destinasi', 'This scanner does not follow redirects. Verify the destination with the sender independently.')
    if re.search(r'(redirect|returnurl|next|url|continue)=https?%?[:3]', unquote(parsed.query), re.I):
        add('redirect_parameter', 20, 'Possible redirect parameter', 'Parameter pengalihan mungkin', 'A query parameter contains another URL; no redirect has been followed or verified.')
    return result(flags, 'und', 'phishing', ascii_host)


def assess_text(text: str) -> Assessment:
    """Public text detector shared by web and bot, with guarded ML fallback."""
    from app.ml.runtime import apply_prediction, get_runtime
    return apply_prediction(analyze_text(text), get_runtime().message, text)


def assess_url(url: str) -> Assessment:
    """Public URL detector; lexical extraction never visits the destination."""
    from app.ml.runtime import apply_prediction, get_runtime
    return apply_prediction(analyze_url(url), get_runtime().url, url)
