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
    Float,
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
    pagename = Column(String, unique=True, nullable=False) # name of the player's Liquipedia page
    name = Column(String) # name from Liquipedia page
    display_name = Column(String)  # name from the rosters on the tournament page  
    alternate_names = Column(String)  # comma-separated list of alternate names
    nationality = Column(String)

    entries = relationship("PlayerEntry", back_populates="player")
    match_rosters = relationship("MatchRoster", back_populates="player")
    accounts = relationship("PlayerAccount", back_populates="player")


class PlayerAccount(Base):
    __tablename__ = "player_accounts"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    account_id = Column(BigInteger)
    note = Column(String)

    player = relationship("Player", back_populates="accounts")


class Vehicles(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)
    tag = Column(String, unique=True, nullable=False)
    name = Column(String)
    type = Column(String)  # "heavyTank", "mediumTank", etc.
    nation = Column(String)  # "USA", "Germany", etc.
    role = Column(String)  # "damageDealer", "support", etc.

    entries = relationship("PlayerEntry", back_populates="vehicle")


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
    arena_unique_id = Column(String, unique=True)  # blocks[1][0].arenaUniqueID
    map = Column(String)  # block[0].mapDisplayName
    game_version = Column(String)  # block[0].clientVersionFromExe
    server = Column(String)  # block[0].serverName or block[0].regionCode
    winner_index = Column(Integer)  # blocks[1][0].common.winnerTeam
    finish_reason = Column(
        Integer
    )  # blocks[1][0].common.finishReason, Have to discover what numbers mean
    duration_sec = Column(Integer)  # blocks[1][0].common.duration
    team1_hp = Column(Integer)  # blocks[1][0].common.teamHealth["1"]
    team2_hp = Column(Integer)  # blocks[1][0].common.teamHealth["2"]
    replay_file = Column(String)  # replay file name
    date_time = Column(DateTime)  # block[0].dateTime

    map_game = relationship("MapGame", back_populates="games")
    entries = relationship("PlayerEntry", back_populates="game")


class PlayerEntry(Base):
    __tablename__ = "player_entries"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"))

    # Identity
    game_entity_id = Column(String)
    name = Column(String)  # blocks[1][1][entity_id].name
    team_index = Column(Integer)  # blocks[1][1][entity_id].team

    # Vehicle
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    # Combat
    kills = Column(Integer)  # blocks[1][0].vehicles[entity_id].kills
    damage_dealt = Column(Integer)  # blocks[1][0].vehicles[entity_id].damageDealt
    sniper_damage_dealt = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].sniperDamageDealt
    damage_assisted_track = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageAssistedTrack
    damage_assisted_radio = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageAssistedRadio
    damage_assisted_stun = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageAssistedStun
    damage_assisted_smoke = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageAssistedSmoke
    damage_assisted_inspire = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageAssistedInspire
    max_hp = Column(Integer)  # blocks[1][0].vehicles[entity_id].maxHealth
    damage_blocked_by_armor = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageBlockedByArmor
    damage_received = Column(Integer)  # blocks[1][0].vehicles[entity_id].damageReceived
    potential_damage_received = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].potentialDamageReceived
    damage_received_from_invisibles = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].damageReceivedFromInvisibles
    end_game_hp = Column(Integer)  # blocks[1][0].vehicles[entity_id].health
    spotted = Column(Integer)  # blocks[1][0].vehicles[entity_id].spotted
    damaged = Column(Integer)  # blocks[1][0].vehicles[entity_id].damaged
    stunned = Column(Integer)  # blocks[1][0].vehicles[entity_id].stunned
    stun_duration = Column(Float)  # blocks[1][0].vehicles[entity_id].stunDuration

    # Shots
    shots = Column(Integer)  # blocks[1][0].vehicles[entity_id].shots
    direct_hits = Column(Integer)  # blocks[1][0].vehicles[entity_id].directHits
    direct_enemy_hits = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].directEnemyHits
    direct_team_hits = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].directTeamHits
    direct_hits_received = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].directHitsReceived
    no_damage_direct_hits_received = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].noDamageDirectHitsReceived
    piercings = Column(Integer)  # blocks[1][0].vehicles[entity_id].piercings
    piercing_enemy_hits = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].piercingEnemyHits
    piercings_received = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].piercingsReceived
    explosion_hits = Column(Integer)  # blocks[1][0].vehicles[entity_id].explosionHits
    explosion_hits_received = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].explosionHitsReceived

    # Team damage
    is_team_killer = Column(Boolean)  # blocks[1][0].vehicles[entity_id].isTeamKiller
    team_kills = Column(Integer)  # blocks[1][0].vehicles[entity_id].tkills
    team_damage_dealt = Column(Integer)  # blocks[1][0].vehicles[entity_id].tdamageDealt
    team_destroyed_modules = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].tdestroyedModules

    # Survival
    survived = Column(Boolean)  # blocks[1][1][entity_id].isAlive
    killed_by_entity = Column(String)  # blocks[1][1].vehicles[entity_id].killerID
    death_reason = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].deathReason, -1 if not killed, gotta figure out what the other numbers mean
    is_first_blood = Column(Boolean)  # blocks[1][0].vehicles[entity_id].isFirstBlood
    mileage_m = Column(Integer)  # blocks[1][0].vehicles[entity_id].mileage
    life_time_sec = Column(Integer)  # blocks[1][0].vehicles[entity_id].lifeTime

    # Objectives
    capture_points = Column(Integer)  # blocks[1][0].vehicles[entity_id].capturePoints
    dropped_capture_points = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].droppedCapturePoints
    vehicle_num_captured = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].vehicleNumCaptured

    # Mode-specific
    onslaught_role_skill_used = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].roleSkillUsed
    onslaught_health_repair = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].healthRepair
    onslaught_allied_health_repair = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].alliedHealthRepair
    onslaught_points_captured_by_own_team = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].poiCapturedByOwnTeam
    resource_absorbed = Column(
        Integer
    )  # blocks[1][0].vehicles[entity_id].resourceAbsorbed
    # Have to chack if these last 2 columns are relevant for onslaught

    game = relationship("Game", back_populates="entries")
    player = relationship("Player", back_populates="entries")
    vehicle = relationship("Vehicles", back_populates="entries")

    # blocks[1][0].vehicles[entity_id].entityCaptured ???
