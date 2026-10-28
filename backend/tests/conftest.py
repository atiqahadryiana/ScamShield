import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.security import RateLimiter
from app.main import app
from app.services.seed import seed
from app.models import entities  # noqa: F401


@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    from sqlalchemy import event
    @event.listens_for(engine, 'connect')
    def fk(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        seed(db)
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    monkeypatch.setattr('app.main.limiter', RateLimiter())
    monkeypatch.setattr('app.main.SessionLocal', factory)
    # API tests must never depend on or call a configured external reputation service.
    monkeypatch.setattr('app.api.routes.check_phishtank', lambda assessment, *_: assessment)
    with TestClient(app, headers={'X-ScamShield-Client': 'web'}) as test:
        yield test
    app.dependency_overrides.clear()
    engine.dispose()
