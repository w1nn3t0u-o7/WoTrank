from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Tournament

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def list_tournaments(db: Session = Depends(get_db)):
    return db.query(Tournament).order_by(Tournament.start_date.desc()).all()
