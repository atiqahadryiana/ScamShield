from sqlalchemy.orm import Session
from app.models.entities import RiskClassification, ScamCategory, ThreatIndicator, LearningModule, QuizQuestion
from app.services.detection import RULES
from app.services.education import seeded_modules


def seed(db: Session) -> None:
    for risk, text in [('LOW', 'No strong indicators; safety is not guaranteed.'), ('MEDIUM', 'Suspicious characteristics require verification.'), ('HIGH', 'Strong scam indicators detected.')]:
        if not db.get(RiskClassification, risk):
            db.add(RiskClassification(id=risk, description=text))
    for key in ['job', 'investment', 'prize', 'impersonation', 'phishing', 'other']:
        if not db.get(ScamCategory, key):
            db.add(ScamCategory(id=key, name=key.title()))
    for key, pattern, weight, title, ms, why, why_ms in RULES:
        if not db.get(ThreatIndicator, key):
            db.add(ThreatIndicator(id=key, definition=dict(pattern=pattern, weight=weight, title=title, title_ms=ms, explanation=why, explanation_ms=why_ms)))
    for module in seeded_modules():
        content = dict(module)
        question = content.pop('question')
        if not db.get(LearningModule, module['id']):
            db.add(LearningModule(id=module['id'], content=content))
            db.flush()
            db.add(QuizQuestion(id=question['id'], module_id=module['id'], content=question))
    db.commit()
