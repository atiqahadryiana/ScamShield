"""Shared, deterministic text preprocessing for training and inference."""
import re
import unicodedata


CONTROL_CHARS = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f]')
WHITESPACE = re.compile(r'\s+')


def normalize_text(value: str) -> str:
    """Normalize text without removing URLs, punctuation, or currency symbols."""
    value = unicodedata.normalize('NFKC', value).casefold()
    value = CONTROL_CHARS.sub('', value)
    return WHITESPACE.sub(' ', value).strip()


def redact_training_text(value: str) -> str:
    """Best-effort de-identification helper; source review is still required."""
    value = re.sub(r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '<EMAIL>', value)
    value = re.sub(r'(?<!\d)(?:\+?60|0)1\d[- ]?\d{3,4}[- ]?\d{4}(?!\d)', '<PHONE>', value)
    value = re.sub(r'(?i)\b(?:otp|tac|code|kod)\s*[:=-]?\s*\d{4,8}\b', '<SECRET_CODE>', value)
    return value
