from sqlmodel import SQLModel, Session, create_engine

from src.config import DATABASE_URL
from src.db.models import SenderIDMapping


engine = create_engine(
    DATABASE_URL,
    echo=False,
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)