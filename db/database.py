from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Swap to PostgreSQL by changing this one line:
# DATABASE_URL = "postgresql://user:password@localhost:5432/wotrank"
DATABASE_URL = "sqlite:///wotrank.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)