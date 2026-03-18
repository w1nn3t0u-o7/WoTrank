from pydantic import BaseModel
from typing import Optional


class PlayerSummary(BaseModel):
    id: int
    display_name: Optional[str]
    nationality: Optional[str]
    games_played: int
    avg_damage: Optional[float]
    avg_kills: Optional[float]
    avg_assisted: Optional[float]
    avg_spotted: Optional[float]
    survival_rate: Optional[float]

    class Config:
        from_attributes = True


class PlayerDetail(PlayerSummary):
    name: Optional[str]
    pagename: str
    avg_blocked: Optional[float]
    avg_shots: Optional[float]
    avg_piercings: Optional[float]


class TeamSummary(BaseModel):
    id: int
    name: str
    wins: int
    losses: int
    total_matches: int


class TournamentSummary(BaseModel):
    id: int
    name: str
    series: Optional[str]
    type: str
    format: str
    mode: Optional[str]
    liquipedia_tier: str
    start_date: str
    end_date: str
