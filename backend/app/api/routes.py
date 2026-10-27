import secrets
import shutil
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import delete, select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import EPHEMERAL_DATABASE, get_db
from app.core.security import optional_user, current_user, admin_user, password_hasher, verify_password, digest
from app.models.entities import User, Session as LoginSession, ScanRecord, AwarenessMetric, LearningModule, QuizQuestion, QuizAttempt, Notice, AuditLog
from app.schemas.requests import ScanInput, URLInput, Credentials, QuizInput, NoticeInput, Assessment, PreferencesInput
from app.services.detection import assess_text, assess_url
from app.services.ocr import extract_text, OCRUnavailable, MAX_BYTES
from app.services.resources import RESOURCES
from app.services.storage import record_metric
from app.services.threat_intelligence import check_phishtank
from app.ml.runtime import get_runtime

router = APIRouter(prefix='/api/v1')
DB = Annotated[Session, Depends(get_db)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
AuthUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]


def store(db: Session, assessment: Assessment, content: str, save: bool, user: User | None):
    if save and user is None:
        raise HTTPException(401, 'Sign in before saving scan history.')
    record_metric(db, assessment, 'web')
    if save:
        db.add(ScanRecord(id=assessment.id, user_id=user.id, content=content, assessment=assessment.model_dump(mode='json'), risk=assessment.risk))
    db.commit()
    return assessment


@router.get('/health')
def health(db: DB):
    db.execute(select(1))
    settings = get_settings()
    ml = get_runtime().status()
    return {'status': 'ok', 'engine': 'explainable-rules-v1' if set(ml.values()) == {'rules_only'} else 'validated-ml-with-rule-explanations-v1', 'ml_status': ml, 'storage': 'ephemeral' if EPHEMERAL_DATABASE else 'persistent', 'ocr_available': bool(shutil.which(settings.tesseract_cmd or 'tesseract')), 'phishtank_configured': bool(settings.phishtank_app_key), 'telegram_configured': bool(settings.telegram_bot_token), 'telegram_username': settings.telegram_bot_username or None}


@router.post('/scan/text', response_model=Assessment)
def scan_text(body: ScanInput, db: DB, user: OptionalUser):
    return store(db, assess_text(body.text), body.text, body.save_history, user)


@router.post('/scan/url', response_model=Assessment)
def scan_url(body: URLInput, db: DB, user: OptionalUser):
    try:
        assessment = assess_url(body.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    settings = get_settings()
    assessment = check_phishtank(assessment, body.url, settings.phishtank_app_key, settings.phishtank_user_agent)
    return store(db, assessment, body.url, body.save_history, user)


@router.post('/scan/image')
def scan_image(file: Annotated[UploadFile, File()]):
    """OCR only. Users review/redact before explicitly submitting extracted text."""
    try:
        data = file.file.read(MAX_BYTES + 1)
        text = extract_text(data, file.content_type or '')
        return {'extracted_text': text, 'requires_review': True, 'retained': False}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except OCRUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    finally:
        file.file.close()


@router.get('/scan/{scan_id}', response_model=Assessment)
def get_scan(scan_id: str, db: DB, user: AuthUser):
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().history_retention_days)
    record = db.scalar(select(ScanRecord).where(ScanRecord.id == scan_id, ScanRecord.user_id == user.id, ScanRecord.created_at >= cutoff))
    if record is None:
        raise HTTPException(404, 'Scan not found or expired.')
    return record.assessment


def user_view(user: User) -> dict:
    return {'id': user.id, 'email': user.email, 'role': user.role, 'preferences': user.preferences}


def set_session(db: Session, user: User, response: Response):
    token = secrets.token_urlsafe(48)
    db.add(LoginSession(token_hash=digest(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
    db.commit()
    response.set_cookie('scamshield_session', token, httponly=True, secure=get_settings().environment == 'production', samesite='strict', max_age=28800, path='/api')


@router.post('/auth/register', status_code=201)
def register(body: Credentials, response: Response, db: DB):
    user = User(email=body.email.casefold(), password_hash=password_hasher.hash(body.password), role='user')
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Unable to register this email. Try signing in.') from None
    set_session(db, user, response)
    return user_view(user)


@router.post('/auth/login')
def login(body: Credentials, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == body.email.casefold()))
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(401, 'Incorrect email or password.')
    set_session(db, user, response)
    return user_view(user)


@router.get('/auth/me')
def me(user: AuthUser):
    return user_view(user)


@router.put('/auth/preferences')
def preferences(body: PreferencesInput, db: DB, user: AuthUser):
    user.preferences = {**user.preferences, **body.model_dump()}
    db.commit()
    return user_view(user)


@router.post('/auth/logout')
def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get('scamshield_session', '')
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(token)))
    db.commit()
    response.delete_cookie('scamshield_session', path='/api')
    return {'ok': True}


@router.get('/history')
def history(db: DB, user: AuthUser):
    cutoff = datetime.now(timezone.utc) - timedelta(days=get_settings().history_retention_days)
    records = db.scalars(select(ScanRecord).where(ScanRecord.user_id == user.id, ScanRecord.created_at >= cutoff).order_by(ScanRecord.created_at.desc()).limit(100)).all()
    return [{'id': r.id, 'risk': r.risk, 'content': r.content, 'assessment': r.assessment, 'created_at': r.created_at.isoformat()} for r in records]


@router.delete('/history')
def delete_history(db: DB, user: AuthUser):
    db.execute(delete(ScanRecord).where(ScanRecord.user_id == user.id))
    db.commit()
    return {'ok': True}


@router.delete('/auth/account')
def delete_account(db: DB, user: AuthUser, response: Response):
    db.delete(user)
    db.commit()
    response.delete_cookie('scamshield_session', path='/api')
    return {'ok': True}


@router.get('/resources')
def resources():
    return {'resources': RESOURCES, 'verified_on': '2026-10-15', 'integration': 'official_links_only', 'independent_project': True}


@router.get('/education/modules')
def modules(db: DB):
    output = []
    for module in db.scalars(select(LearningModule)).all():
        questions = db.scalars(select(QuizQuestion).where(QuizQuestion.module_id == module.id)).all()
        output.append({**module.content, 'questions': [{k: v for k, v in q.content.items() if k not in ('correct', 'explanation')} for q in questions]})
    return output


@router.post('/education/quiz')
def quiz(body: QuizInput, db: DB, user: OptionalUser):
    questions = db.scalars(select(QuizQuestion).where(QuizQuestion.module_id == body.module_id)).all()
    if not questions or len(body.answers) != len(questions):
        raise HTTPException(422, 'Submit one answer for every question in a valid module.')
    if any(answer < 0 or answer >= len(q.content['options']) for answer, q in zip(body.answers, questions)):
        raise HTTPException(422, 'Invalid answer option.')
    results = [{'correct': q.content['correct'], 'is_correct': answer == q.content['correct'], 'explanation': q.content['explanation']} for answer, q in zip(body.answers, questions)]
    score = sum(item['is_correct'] for item in results)
    db.add(QuizAttempt(user_id=user.id if user else None, module_id=body.module_id, stage=body.stage, score=score, total=len(questions)))
    db.commit()
    return {'score': score, 'total': len(questions), 'results': results, 'stage': body.stage}


@router.get('/education/progress')
def progress(db: DB, user: AuthUser):
    attempts = db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user.id).order_by(QuizAttempt.created_at)).all()
    return [{'module_id': q.module_id, 'stage': q.stage, 'score': q.score, 'total': q.total} for q in attempts]


@router.get('/dashboard/summary')
def summary(db: DB):
    metrics = db.scalars(select(AwarenessMetric)).all()
    risk, categories, languages, channels, daily = (defaultdict(int) for _ in range(5))
    for row in metrics:
        risk[row.risk] += row.count
        categories[row.category] += row.count
        languages[row.language] += row.count
        channels[row.channel] += row.count
        daily[row.day] += row.count
    attempts = db.scalars(select(QuizAttempt)).all()
    # No private input, identities, bank details or exact scan timestamps.
    return {'source': 'installation_aggregate_activity', 'is_demo': False, 'total_scans': sum(risk.values()), 'risk': dict(risk), 'categories': dict(categories), 'languages': dict(languages), 'channels': dict(channels), 'daily': [{'date': key, 'scans': value} for key, value in sorted(daily.items())[-30:]], 'quiz_attempts': len(attempts), 'learning_completions': sum(q.stage == 'post' and q.score == q.total for q in attempts), 'pre_assessment_average': sum(q.score / q.total for q in attempts if q.stage == 'pre') / max(1, sum(q.stage == 'pre' for q in attempts)), 'post_assessment_average': sum(q.score / q.total for q in attempts if q.stage == 'post') / max(1, sum(q.stage == 'post' for q in attempts)), 'notices': [{'id': n.id, 'title': n.title, 'body': n.body} for n in db.scalars(select(Notice).order_by(Notice.created_at.desc()).limit(5)).all()]}


@router.get('/admin/overview')
def admin_overview(db: DB, user: AdminUser):
    return {'summary': summary(db), 'user_count': db.scalar(select(func.count(User.id))), 'audit': [{'action': a.action, 'target_id': a.target_id, 'created_at': a.created_at.isoformat()} for a in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(30)).all()]}


@router.post('/admin/notices', status_code=201)
def add_notice(body: NoticeInput, db: DB, user: AdminUser):
    notice = Notice(title=body.title, body=body.body)
    db.add(notice)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action='notice_created', target_id=notice.id))
    db.commit()
    return {'id': notice.id}


@router.delete('/admin/notices/{notice_id}')
def remove_notice(notice_id: str, db: DB, user: AdminUser):
    notice = db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(404, 'Notice not found.')
    db.delete(notice)
    db.add(AuditLog(actor_id=user.id, action='notice_deleted', target_id=notice_id))
    db.commit()
    return {'ok': True}


@router.put('/admin/modules/{module_id}')
def edit_module(module_id: str, body: NoticeInput, db: DB, user: AdminUser):
    module = db.get(LearningModule, module_id)
    if not module:
        raise HTTPException(404, 'Module not found.')
    module.content = {**module.content, 'title': body.title, 'lesson': body.body}
    db.add(AuditLog(actor_id=user.id, action='module_updated', target_id=module_id))
    db.commit()
    return {'ok': True}
