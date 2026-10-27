"""Network-free lexical URL features. This module never resolves or fetches URLs."""
from __future__ import annotations

import ipaddress
import math
import re
from urllib.parse import urlsplit

FEATURE_NAMES = [
    'url_length', 'host_length', 'path_length', 'query_length', 'dot_count',
    'subdomain_count', 'digit_ratio', 'special_count', 'hyphen_count',
    'at_count', 'percent_count', 'uses_http', 'host_is_ip', 'has_punycode',
    'suspicious_word_count', 'entropy',
]
SUSPICIOUS_WORDS = re.compile(r'(?i)(login|verify|secure|account|update|confirm|wallet|bank|bonus|prize|claim|otp)')


def parse_url(raw: str):
    raw = raw.strip()
    if len(raw) > 2048 or re.search(r'[\s\x00-\x1f\\]', raw):
        raise ValueError('Invalid URL.')
    parsed = urlsplit(raw if '://' in raw else 'https://' + raw)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Only HTTP and HTTPS URLs are supported.')
    try:
        _ = parsed.port
        host = parsed.hostname.encode('idna').decode('ascii').lower()
    except (ValueError, UnicodeError):
        raise ValueError('Invalid URL host or port.') from None
    return raw, parsed, host


def _entropy(value: str) -> float:
    if not value:
        return 0.0
    return -sum((value.count(char) / len(value)) * math.log2(value.count(char) / len(value)) for char in set(value))


def extract_url_features(raw: str) -> list[float]:
    raw, parsed, host = parse_url(raw)
    try:
        ipaddress.ip_address(host)
        host_is_ip = 1.0
    except ValueError:
        host_is_ip = 0.0
    digits = sum(char.isdigit() for char in raw)
    labels = host.split('.')
    return [
        float(len(raw)), float(len(host)), float(len(parsed.path)), float(len(parsed.query)),
        float(host.count('.')), float(max(0, len(labels) - 2)), float(digits / max(1, len(raw))),
        float(sum(not char.isalnum() for char in raw)), float(raw.count('-')), float(raw.count('@')),
        float(raw.count('%')), float(parsed.scheme == 'http'), host_is_ip, float('xn--' in host),
        float(len(SUSPICIOUS_WORDS.findall(raw))), float(_entropy(host)),
    ]


def extract_many(urls) -> list[list[float]]:
    return [extract_url_features(url) for url in urls]
