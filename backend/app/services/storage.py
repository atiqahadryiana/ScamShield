from datetime import datetime, timedelta, timezone
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.entities import AwarenessMetric, ScanRecord, Session as LoginSession
from app.schemas.requests import Assessment


def record_metric(db: Session, assessment: Assessment, channel: str) -> None:
    values = dict(day=datetime.now(timezone.utc).date().isoformat(), channel=channel, risk=assessment.risk, category=assessment.category, language=assessment.language, count=1)
    # Atomic upsert avoids lost updates in simultaneous web/bot scans.
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(AwarenessMetric).values(**values)
    statement = statement.on_conflict_do_update(index_elements=['day', 'channel', 'risk', 'category', 'language'], set_={'count': AwarenessMetric.count + 1})
    db.execute(statement)


def cleanup(db: Session) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().history_retention_days)
    scans = db.execute(delete(ScanRecord).where(ScanRecord.created_at < cutoff)).rowcount
    sessions = db.execute(delete(LoginSession).where(LoginSession.expires_at < datetime.now(timezone.utc))).rowcount
    db.commit()
    return {'expired_scans_deleted': scans, 'expired_sessions_deleted': sessions}
