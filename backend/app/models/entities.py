import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='user')
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Session(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RiskClassification(Base):
    __tablename__ = 'risk_classifications'
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    description: Mapped[str] = mapped_column(Text)


class ScamCategory(Base):
    __tablename__ = 'scam_categories'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class ThreatIndicator(Base):
    __tablename__ = 'threat_indicators'
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    definition: Mapped[dict] = mapped_column(JSON)


class ScanRecord(Base):
    __tablename__ = 'scan_records'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    content: Mapped[str] = mapped_column(Text)
    assessment: Mapped[dict] = mapped_column(JSON)
    risk: Mapped[str] = mapped_column(ForeignKey('risk_classifications.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class AwarenessMetric(Base):
    __tablename__ = 'awareness_metrics'
    __table_args__ = (UniqueConstraint('day', 'channel', 'risk', 'category', 'language'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[str] = mapped_column(String(10), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    risk: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(40))
    language: Mapped[str] = mapped_column(String(16))
    count: Mapped[int] = mapped_column(Integer, default=0)


class LearningModule(Base):
    __tablename__ = 'learning_modules'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    content: Mapped[dict] = mapped_column(JSON)


class QuizQuestion(Base):
    __tablename__ = 'quiz_questions'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    module_id: Mapped[str] = mapped_column(ForeignKey('learning_modules.id', ondelete='CASCADE'))
    content: Mapped[dict] = mapped_column(JSON)


class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    module_id: Mapped[str] = mapped_column(ForeignKey('learning_modules.id'))
    stage: Mapped[str] = mapped_column(String(10))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Notice(Base):
    __tablename__ = 'notices'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = 'admin_audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
