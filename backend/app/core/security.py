import hashlib
import secrets
import time
from collections import deque
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session as DBSession
from app.core.database import get_db
from app.models.entities import Session, User

password_hasher = PasswordHash.recommended()
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def optional_user(request: Request, db: DBSession = Depends(get_db)) -> User | None:
    token = request.cookies.get('scamshield_session')
    if not token:
        return None
    session = db.get(Session, digest(token))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return db.get(User, session.user_id)


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(401, 'Sign in to use this feature.')
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != 'admin':
        raise HTTPException(403, 'Administrator access required.')
    return user


def verify_password(password: str, stored: str | None) -> bool:
    return password_hasher.verify(password, stored or _dummy_hash) and stored is not None


class RateLimiter:
    """Ephemeral salted keys, bounded storage. Deploy one process or use a gateway limit."""
    def __init__(self):
        self.salt = secrets.token_bytes(32)
        self.buckets: dict[str, deque] = {}

    def allow(self, identity: str, limit: int) -> bool:
        key = hashlib.sha256(self.salt + identity.encode()).hexdigest()
        now = time.monotonic()
        if len(self.buckets) > 10000:
            self.buckets = {k: v for k, v in self.buckets.items() if v and v[-1] > now - 60}
            if len(self.buckets) > 10000 and key not in self.buckets:
                return False
        bucket = self.buckets.setdefault(key, deque())
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True
