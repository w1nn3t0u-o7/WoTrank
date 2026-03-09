from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean,
    DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass

class Tournament(Base):
    __tablename__ = "tournaments"

    id          = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True, nullable=False)
    name        = Column(String, unique=True, nullable=False)
    series      = Column(String)   # "Onslaught Legends Cup" etc.
    type        = Column(String, nullable=False)   # Offline or Online
    location    = Column(String)
    server      = Column(String)   # "EU", "NA", etc.
    format      = Column(String, nullable=False)    # 7v7, 15v15, etc.
    mode        = Column(String)    # "Standard", "Onslaught", "Attack/Defense", etc.
    start_date  = Column(DateTime, nullable=False)
    end_date    = Column(DateTime, nullable=False)
    liquipedia_tier = Column(String, nullable=False)  # "S", "A", "B", etc.

    matches = relationship("Match", back_populates="tournament")

class Team(Base):
    __tablename__ = "teams"

    id          = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True)
    name        = Column(String, unique=True, nullable=False)
    template = Column(String, unique=True, nullable=False)
    

class Player(Base):
    __tablename__ = "players"

    id          = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True)
    page_name        = Column(String, unique=True, nullable=False)
    name = Column(String)
    alternate_names = Column(String)  # comma-separated list of alternate names
    nationality = Column(String)
    account_id  = Column(BigInteger, unique=True)

    entries = relationship("PlayerEntry", back_populates="player")

class Match(Base):
    __tablename__ = "matches"

    id               = Column(Integer, primary_key=True)
    tournament_id    = Column(Integer, ForeignKey("tournaments.id"))
    liquipedia_id    = Column(String, unique=True)
    stage            = Column(String)   # "Group Stage", "Playoffs", etc.
    round            = Column(String)   # "Round of 16", "Quarterfinals", etc.
    team1_id         = Column(Integer, ForeignKey("teams.id"))
    team1_score      = Column(Integer)
    team2_id         = Column(Integer, ForeignKey("teams.id"))
    team2_score      = Column(Integer)
    winner_team_id   = Column(Integer, ForeignKey("teams.id"))
    best_of          = Column(Integer)   # 1, 3, 5, etc.
    datetime         = Column(DateTime)

    tournament = relationship("Tournament", back_populates="matches")
    rounds = relationship("Round", back_populates="match")

class Round(Base):
    __tablename__ = "rounds"

    id               = Column(Integer, primary_key=True)
    match_id         = Column(Integer, ForeignKey("matches.id"))
    round_number     = Column(Integer)   # 1, 2, 3, etc.
    arena_unique_id  = Column(String, unique=True, nullable=False)  # deduplication key
    replay_file      = Column(String)
    date_time        = Column(DateTime)
    map_name         = Column(String)
    map_display_name = Column(String)
    gameplay_id      = Column(String)
    battle_type      = Column(Integer)
    bonus_type       = Column(Integer)   # 14 = CW/tournament
    duration_sec     = Column(Integer)
    winner_team      = Column(Integer)
    wot_version      = Column(String)
    server_name      = Column(String)
    recorder_name    = Column(String)
    recorder_id      = Column(BigInteger)
    source           = Column(String, default="replay")  # "replay" | "manual"

    match = relationship("Match", back_populates="rounds")
    entries = relationship("PlayerEntry", back_populates="round")


class PlayerEntry(Base):
    __tablename__ = "player_entries"

    id         = Column(Integer, primary_key=True)
    round_id   = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    match_id   = Column(Integer, ForeignKey("matches.id"))
    player_id  = Column(Integer, ForeignKey("players.id"))

    # Identity (filled from block0 vehicles / block1 roster + players dict)
    account_id = Column(BigInteger)
    name       = Column(String)
    clan       = Column(String)
    team       = Column(Integer)
    entity_id  = Column(String)

    # Vehicle
    vehicle_type   = Column(String)   # "germany:G125_Spz_57_Rh"
    vehicle_nation = Column(String)   # "germany"
    vehicle_tag    = Column(String)   # "G125_Spz_57_Rh"

    # Core performance
    kills                    = Column(Integer)
    damage_dealt             = Column(Integer)
    damage_assisted_radio    = Column(Integer)
    damage_assisted_track    = Column(Integer)
    damage_assisted_stun     = Column(Integer)
    damage_assisted_inspire  = Column(Integer)
    damage_assisted_smoke    = Column(Integer)
    damage_blocked           = Column(Integer)
    damage_received          = Column(Integer)
    spotted                  = Column(Integer)

    # Shots
    shots              = Column(Integer)
    direct_hits        = Column(Integer)
    piercings          = Column(Integer)
    piercings_received = Column(Integer)

    # Survival
    survived            = Column(Boolean)
    life_time_sec       = Column(Integer)
    death_reason        = Column(Integer)   # -1 = survived
    killed_by_entity_id = Column(String)    # from deathInfo.killerID

    # Economy
    xp      = Column(Integer)
    credits = Column(Integer)

    # Data quality
    source = Column(String, default="replay")   # "replay" | "manual"

    round = relationship("Round", back_populates="entries")
    player = relationship("Player", back_populates="entries")