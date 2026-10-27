import os
import tempfile

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


configured_url = os.getenv('DATABASE_URL', '').strip()
# Vercel Functions cannot write to the deployed project directory. Keep the
# public demo usable when no managed database has been attached by placing its
# non-durable SQLite database in the function's writable scratch directory.
EPHEMERAL_DATABASE = os.getenv('VERCEL') == '1' and not configured_url
url = f"sqlite:///{os.path.join(tempfile.gettempdir(), 'scamshield.db')}" if EPHEMERAL_DATABASE else get_settings().database_url
engine = create_engine(url, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
if url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA secure_delete=ON')

SessionLocal = sessionmaker(bind=engine)


def get_db():
    with SessionLocal() as db:
        yield db
