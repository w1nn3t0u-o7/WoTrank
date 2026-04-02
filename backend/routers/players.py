from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from backend.schemas import PlayerDetail, PlayerSummary
from db.database import SessionLocal
from db.models import Match, MatchRoster, Player, PlayerEntry

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _player_stats_query(db: Session, tournament_id: Optional[int] = None):
    assisted = PlayerEntry.damage_assisted_track + PlayerEntry.damage_assisted_radio

    q = db.query(
        Player.id,
        Player.display_name,
        Player.nationality,
        func.count(PlayerEntry.id).label("games_played"),
        func.avg(PlayerEntry.damage_dealt).label("avg_damage"),
        func.avg(PlayerEntry.kills).label("avg_kills"),
        func.avg(assisted).label("avg_assisted"),
        func.avg(PlayerEntry.spotted).label("avg_spotted"),
        func.avg(PlayerEntry.damage_blocked_by_armor).label("avg_blocked"),
        func.avg(cast(PlayerEntry.survived, Integer)).label("survival_rate"),
    ).join(PlayerEntry, Player.id == PlayerEntry.player_id)
    if tournament_id:
        q = (
            q.join(MatchRoster, MatchRoster.player_id == Player.id)
            .join(Match, Match.id == MatchRoster.match_id)
            .filter(Match.tournament_id == tournament_id)
        )
    return q.group_by(Player.id).having(func.count(PlayerEntry.id) >= 5)


@router.get("/", response_model=list[PlayerSummary])
def list_players(
    tournament_id: Optional[int] = None,
    sort_by: str = Query(
        "avg_damage",
        enum=[
            "avg_damage",
            "avg_kills",
            "avg_assisted",
            "avg_spotted",
            "survival_rate",
        ],
    ),
    min_games: int = 5,
    db: Session = Depends(get_db),
):
    q = _player_stats_query(db, tournament_id)
    rows = q.order_by(func.avg(PlayerEntry.damage_dealt).desc()).all()
    return [PlayerSummary(**r._asdict()) for r in rows]


@router.get("/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, db: Session = Depends(get_db)):
    row = _player_stats_query(db).filter(Player.id == player_id).first()
    if not row:
        from fastapi import HTTPException

        raise HTTPException(404, "Player not found")
    return PlayerDetail(**row._asdict())
