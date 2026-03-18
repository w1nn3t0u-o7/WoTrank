from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.database import SessionLocal
from db.models import PlayerEntry, Vehicles, Game

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/vehicles")
def vehicle_usage(db: Session = Depends(get_db)):
    return (
        db.query(
            Vehicles.name,
            Vehicles.type,
            func.count(PlayerEntry.id).label("times_played"),
            func.avg(PlayerEntry.damage_dealt).label("avg_damage"),
            func.avg(PlayerEntry.kills).label("avg_kills"),
        )
        .join(PlayerEntry, Vehicles.id == PlayerEntry.vehicle_id)
        .group_by(Vehicles.id)
        .order_by(func.count(PlayerEntry.id).desc())
        .limit(30)
        .all()
    )


@router.get("/maps")
def map_stats(db: Session = Depends(get_db)):
    return (
        db.query(
            Game.map,
            func.count(Game.id).label("games_played"),
            func.avg(Game.duration_sec).label("avg_duration_sec"),
        )
        .filter(Game.map.isnot(None))
        .group_by(Game.map)
        .order_by(func.count(Game.id).desc())
        .all()
    )
