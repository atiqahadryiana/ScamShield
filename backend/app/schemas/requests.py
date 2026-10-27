from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ScanInput(BaseModel):
    text: str = Field(min_length=3, max_length=10000)
    save_history: bool = False

    @field_validator('text')
    @classmethod
    def clean(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Enter at least 3 characters.')
        return v


class URLInput(BaseModel):
    url: str = Field(min_length=4, max_length=2048)
    save_history: bool = False


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=10, max_length=128)


class QuizInput(BaseModel):
    module_id: str
    answers: list[int] = Field(min_length=1, max_length=10)
    stage: Literal['pre', 'post'] = 'post'


class NoticeInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=3, max_length=2000)


class PreferencesInput(BaseModel):
    dashboard_days: Literal[7, 30] = 30


class Indicator(BaseModel):
    id: str
    title: str
    title_ms: str
    explanation: str
    explanation_ms: str
    weight: int


class Assessment(BaseModel):
    id: str
    risk: Literal['LOW', 'MEDIUM', 'HIGH']
    score: int
    score_type: str = 'heuristic_indicator_score'
    model_probability: float | None = None
    engine: str = 'explainable-rules-v1'
    language: str
    category: str
    indicators: list[Indicator]
    recommendations: list[str]
    recommendations_ms: list[str]
    disclaimer: str
    disclaimer_ms: str
    created_at: str
    domain: str | None = None
    threat_intelligence: str = 'not_configured'
