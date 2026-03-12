from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True, nullable=False)
    pagename = Column(String, unique=True, nullable=False)
    name = Column(String, unique=True, nullable=False)
    series = Column(String)  # "Onslaught Legends Cup" etc.
    type = Column(String, nullable=False)  # Offline or Online
    location = Column(String)
    server = Column(String)  # "EU", "NA", etc.
    format = Column(String, nullable=False)  # 7v7, 15v15, etc.
    mode = Column(String)  # "Standard", "Onslaught", "Attack/Defense", etc.
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    liquipedia_tier = Column(String, nullable=False)  # "S", "A", "B", etc.

    matches = relationship("Match", back_populates="tournament")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True)
    name = Column(String, unique=True, nullable=False)
    template = Column(String, unique=True, nullable=False)

    map_vetos = relationship("MapVeto", back_populates="team")
    match_rosters = relationship("MatchRoster", back_populates="team")
    team1_matches = relationship(
        "Match", back_populates="team1", foreign_keys="Match.team1_id"
    )
    team2_matches = relationship(
        "Match", back_populates="team2", foreign_keys="Match.team2_id"
    )
    won_matches = relationship(
        "Match", back_populates="winner", foreign_keys="Match.winner_id"
    )


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    liquipedia_id = Column(Integer, unique=True)
    pagename = Column(String, unique=True, nullable=False)
    name = Column(String)
    alternate_names = Column(String)  # comma-separated list of alternate names
    nationality = Column(String)
    account_id = Column(BigInteger, unique=True)

    entries = relationship("PlayerEntry", back_populates="player")
    match_rosters = relationship("MatchRoster", back_populates="player")


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"))
    liquipedia_id = Column(String, unique=True)
    stage = Column(String)  # "Group Stage", "Playoffs", etc.
    round = Column(String)  # "Round of 16", "Quarterfinals", etc.
    best_of = Column(Integer)  # 1, 3, 5, etc.
    team1_id = Column(Integer, ForeignKey("teams.id"))
    team1_score = Column(Integer)
    team2_id = Column(Integer, ForeignKey("teams.id"))
    team2_score = Column(Integer)
    winner_id = Column(Integer, ForeignKey("teams.id"))
    date_time = Column(DateTime)

    tournament = relationship("Tournament", back_populates="matches")
    map_games = relationship("MapGame", back_populates="match")
    map_vetos = relationship("MapVeto", back_populates="match")
    rosters = relationship("MatchRoster", back_populates="match")

    team1 = relationship(
        "Team", back_populates="team1_matches", foreign_keys=[team1_id]
    )
    team2 = relationship(
        "Team", back_populates="team2_matches", foreign_keys=[team2_id]
    )
    winner = relationship(
        "Team", back_populates="won_matches", foreign_keys=[winner_id]
    )


class MapVeto(Base):
    __tablename__ = "map_vetos"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    map = Column(String)
    type = Column(String)  # "ban" or "pick"
    order = Column(Integer)  # 1, 2, 3, etc.

    match = relationship("Match", back_populates="map_vetos")
    team = relationship("Team", back_populates="map_vetos")
    map_game = relationship(
        "MapGame", back_populates="map_veto", uselist=False
    )  # one-to-one relationship, a veto can be linked to at most one map game


class MapGame(Base):
    __tablename__ = "map_games"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    game_index = Column(Integer)  # 0, 1, 2, etc.
    map = Column(String, nullable=False)
    veto_id = Column(Integer, ForeignKey("map_vetos.id"), nullable=True)
    team1_score = Column(Integer)
    team2_score = Column(Integer)
    winner_index = Column(Integer)  # 1 or 2 or 0 for draw
    result_type = Column(
        String
    )  # "draw" or "np", where "np" = not played, None if won by score
    vod_url = Column(String)

    match = relationship("Match", back_populates="map_games")
    games = relationship("Game", back_populates="map_game")
    map_veto = relationship("MapVeto", back_populates="map_game")


class MatchRoster(Base):
    __tablename__ = "match_rosters"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_match_roster"),
    )

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)

    match = relationship("Match", back_populates="rosters")
    player = relationship("Player", back_populates="match_rosters")
    team = relationship("Team", back_populates="match_rosters")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    map_game_id = Column(Integer, ForeignKey("map_games.id"))
    

    map_game = relationship("MapGame", back_populates="games")
    entries = relationship("PlayerEntry", back_populates="game")


class PlayerEntry(Base):
    __tablename__ = "player_entries"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"))


    game = relationship("Game", back_populates="entries")
    player = relationship("Player", back_populates="entries")
