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
    pagename     = Column(String, unique=True, nullable=False)
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
    pagename        = Column(String, unique=True, nullable=False)
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
    best_of          = Column(Integer)   # 1, 3, 5, etc.
    team1_id         = Column(Integer, ForeignKey("teams.id"))
    team1_score      = Column(Integer)
    team2_id         = Column(Integer, ForeignKey("teams.id"))
    team2_score      = Column(Integer)
    winner_team_id   = Column(Integer, ForeignKey("teams.id"))
    datetime         = Column(DateTime)

    tournament = relationship("Tournament", back_populates="matches")
    map_games = relationship("MapGame", back_populates="match")
    map_vetos = relationship("MapVeto", back_populates="match")

class MapVeto(Base):
    __tablename__ = "map_vetos"

    id               = Column(Integer, primary_key=True)
    match_id         = Column(Integer, ForeignKey("matches.id"))
    team_id          = Column(Integer, ForeignKey("teams.id"))
    map              = Column(String)
    type             = Column(String)    # "ban" or "pick"
    order            = Column(Integer)   # 1, 2, 3, etc.

    match = relationship("Match", back_populates="map_vetos")

class MapGame(Base):
    __tablename__ = "map_games"

    id               = Column(Integer, primary_key=True)
    match_id         = Column(Integer, ForeignKey("matches.id"), nullable=False)
    game_index       = Column(Integer)   # 0, 1, 2, etc.
    map              = Column(String, nullable=False)
    veto_id          = Column(Integer, ForeignKey("map_vetos.id"), nullable=True)
    team1_score      = Column(Integer)
    team2_score      = Column(Integer)
    winner           = Column(Integer)   # 1 or 2 or 0 for draw
    result_type      = Column(String)    # "draw" or "np", where "np" = not played, None if won by score
    vod_url          = Column(String)

    match = relationship("Match", back_populates="map_games")
    games = relationship("Game", back_populates="map_game")

class Game(Base):
    __tablename__ = "games"

    id               = Column(Integer, primary_key=True)
    map_game_id      = Column(Integer, ForeignKey("map_games.id"))
    # round_number     = Column(Integer)   # 1, 2, 3, etc.
    arena_unique_id  = Column(String, unique=True)  # deduplication key, from the replay
    date_time        = Column(DateTime) # from the replay
    duration         = Column(Integer) # from the replay
    winner_team      = Column(Integer)
    wot_version      = Column(String)
    source           = Column(String, default="replay")  # "replay" | "manual"
    replay_file      = Column(String)

    map_game = relationship("MapGame", back_populates="games")
    entries = relationship("PlayerEntry", back_populates="game")


class PlayerEntry(Base):
    __tablename__ = "player_entries"

    id         = Column(Integer, primary_key=True)
    game_id    = Column(Integer, ForeignKey("games.id"), nullable=False)
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

    game = relationship("Game", back_populates="entries")
    player = relationship("Player", back_populates="entries")