import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)
