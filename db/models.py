from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import BigInteger, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ENUMS


class TournamentType(StrEnum):
    OFFLINE = "Offline"
    ONLINE = "Online"


class TournamentServer(StrEnum):
    EU = "EU"
    NA = "NA"
    WORLD = "World"


class TournamentFormat(StrEnum):
    SEVEN_V_SEVEN = "7v7"
    FIFTEEN_V_FIFTEEN = "15v15"


class TournamentMode(StrEnum):
    STANDARD = "Standard"
    ONSLAUGHT = "Onslaught"
    ATTACK_DEFENSE = "Attack/Defense"


class TournamentTier(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class VehicleType(StrEnum):
    HEAVY_TANK = "HT"
    MEDIUM_TANK = "MT"
    LIGHT_TANK = "LT"
    TANK_DESTROYER = "TD"
    SPG = "SPG"


class VehicleNation(StrEnum):
    USA = "USA"
    GERMANY = "Germany"
    USSR = "USSR"
    CHINA = "China"
    FRANCE = "France"
    UK = "UK"
    JAPAN = "Japan"


class VehicleRole(StrEnum):
    DAMAGE_DEALER = "damageDealer"
    SUPPORT = "support"
    SCOUT = "scout"
    SNIPER = "sniper"
    # These are just examples, need to figure out the actual roles used in the replays


class MapVetoType(StrEnum):
    BAN = "ban"
    PICK = "pick"
    DECIDER = "decider"


# TABLES


class Base(DeclarativeBase):
    pass


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    liquipedia_id: Mapped[int] = mapped_column(unique=True)
    pagename: Mapped[str] = mapped_column(
        String(100), unique=True
    )  # name of the tournament's Liquipedia page
    name: Mapped[str] = mapped_column(String(100), unique=True)
    series: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # "Onslaught Legends Cup" etc.
    type: Mapped[TournamentType] = mapped_column(
        SAEnum(TournamentType, native_enum=False, validate_strings=True)
    )  # Offline or Online
    location: Mapped[Optional[str]] = mapped_column(String(50))
    server: Mapped[Optional[TournamentServer]] = mapped_column(
        SAEnum(TournamentServer, native_enum=False, validate_strings=True)
    )  # "EU", "NA", etc.
    format: Mapped[TournamentFormat] = mapped_column(
        SAEnum(TournamentFormat, native_enum=False, validate_strings=True)
    )  # 7v7, 15v15, etc.
    mode: Mapped[Optional[TournamentMode]] = mapped_column(
        SAEnum(TournamentMode, native_enum=False, validate_strings=True)
    )  # "Standard", "Onslaught", "Attack/Defense", etc.
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    liquipedia_tier: Mapped[TournamentTier] = mapped_column(
        SAEnum(TournamentTier, native_enum=False, validate_strings=True)
    )  # "S", "A", "B", etc.

    matches: Mapped[list["Match"]] = relationship(back_populates="tournament")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    liquipedia_id: Mapped[Optional[int]] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    template: Mapped[str] = mapped_column(String(30), unique=True)

    map_vetos: Mapped[list["MapVeto"]] = relationship(back_populates="team")
    match_rosters: Mapped[list["MatchRoster"]] = relationship(back_populates="team")
    team1_matches: Mapped[list["Match"]] = relationship(
        back_populates="team1", foreign_keys="Match.team1_id"
    )
    team2_matches: Mapped[list["Match"]] = relationship(
        back_populates="team2", foreign_keys="Match.team2_id"
    )
    won_matches: Mapped[list["Match"]] = relationship(
        back_populates="winner", foreign_keys="Match.winner_id"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    liquipedia_id: Mapped[Optional[int]] = mapped_column(unique=True)
    pagename: Mapped[str] = mapped_column(
        String(100), unique=True
    )  # name of the player's Liquipedia page
    name: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # name from Liquipedia page
    display_name: Mapped[str] = mapped_column(
        String(100)
    )  # name from the rosters on the tournament page
    alternate_names: Mapped[Optional[str]] = mapped_column(
        String(200)
    )  # comma-separated list of alternate names
    nationality: Mapped[Optional[str]] = mapped_column(String(50))

    entries: Mapped[list["PlayerEntry"]] = relationship(back_populates="player")
    match_rosters: Mapped[list["MatchRoster"]] = relationship(back_populates="player")
    accounts: Mapped[list["PlayerAccount"]] = relationship(back_populates="player")


class PlayerAccount(Base):
    __tablename__ = "player_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    account_id: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[Optional[str]] = mapped_column(String(100))

    player: Mapped["Player"] = relationship(back_populates="accounts")


class Vehicles(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(70), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    type: Mapped[VehicleType] = mapped_column(
        SAEnum(VehicleType, native_enum=False, validate_strings=True)
    )
    nation: Mapped[VehicleNation] = mapped_column(
        SAEnum(VehicleNation, native_enum=False, validate_strings=True)
    )
    role: Mapped[VehicleRole] = mapped_column(
        SAEnum(VehicleRole, native_enum=False, validate_strings=True)
    )

    entries: Mapped[list["PlayerEntry"]] = relationship(back_populates="vehicle")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"))
    liquipedia_id: Mapped[str] = mapped_column(String(30), unique=True)
    stage: Mapped[str] = mapped_column(String(30))  # "Group Stage", "Playoffs", etc.
    round: Mapped[Optional[str]] = mapped_column(
        String(30)
    )  # "Round of 16", "Quarterfinals", etc.
    best_of: Mapped[int] = mapped_column()  # 1, 3, 5, etc.
    team1_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    team1_score: Mapped[int] = mapped_column()
    team2_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    team2_score: Mapped[int] = mapped_column()
    winner_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    tournament: Mapped["Tournament"] = relationship(back_populates="matches")
    map_games: Mapped[list["MapGame"]] = relationship(back_populates="match")
    map_vetos: Mapped[list["MapVeto"]] = relationship(back_populates="match")
    rosters: Mapped[list["MatchRoster"]] = relationship(back_populates="match")

    team1: Mapped["Team"] = relationship(
        back_populates="team1_matches", foreign_keys=[team1_id]
    )
    team2: Mapped["Team"] = relationship(
        back_populates="team2_matches", foreign_keys=[team2_id]
    )
    winner: Mapped["Team"] = relationship(
        back_populates="won_matches", foreign_keys=[winner_id]
    )


class MapVeto(Base):
    __tablename__ = "map_vetos"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"))
    map: Mapped[str] = mapped_column(String(20))
    type: Mapped[MapVetoType] = mapped_column(
        SAEnum(MapVetoType, native_enum=False, validate_strings=True)
    )  # "ban" or "pick"
    order: Mapped[int] = mapped_column()  # 1, 2, 3, etc.

    match: Mapped["Match"] = relationship(back_populates="map_vetos")
    team: Mapped["Team"] = relationship(back_populates="map_vetos")
    map_game: Mapped["MapGame"] = relationship(
        back_populates="map_veto", uselist=False
    )  # one-to-one relationship, a veto can be linked to at most one map game


class MapGame(Base):
    __tablename__ = "map_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    game_index: Mapped[int] = mapped_column()  # 0, 1, 2, etc.
    map: Mapped[str] = mapped_column(String(20))
    veto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("map_vetos.id"))
    team1_score: Mapped[Optional[int]] = mapped_column()
    team2_score: Mapped[Optional[int]] = mapped_column()
    winner_index: Mapped[Optional[int]] = mapped_column()  # 1 or 2 or 0 for draw
    result_type: Mapped[Optional[str]] = mapped_column(
        String(10)
    )  # "draw" or "np", where "np" = not played, None if won by score
    vod_url: Mapped[Optional[str]] = mapped_column(String(200))

    match: Mapped["Match"] = relationship(back_populates="map_games")
    games: Mapped[list["Game"]] = relationship(back_populates="map_game")
    map_veto: Mapped["MapVeto"] = relationship(back_populates="map_game")


class MatchRoster(Base):
    __tablename__ = "match_rosters"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_match_roster"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))

    match: Mapped["Match"] = relationship(back_populates="rosters")
    player: Mapped["Player"] = relationship(back_populates="match_rosters")
    team: Mapped["Team"] = relationship(back_populates="match_rosters")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    map_game_id: Mapped[int] = mapped_column(ForeignKey("map_games.id"))
    arena_unique_id: Mapped[str] = mapped_column(
        String(30), unique=True
    )  # blocks[1][0].arenaUniqueID
    map: Mapped[str] = mapped_column(String(20))  # block[0].mapDisplayName
    game_version: Mapped[str] = mapped_column(
        String(20)
    )  # block[0].clientVersionFromExe
    server: Mapped[str] = mapped_column(
        String(20)
    )  # block[0].serverName or block[0].regionCode
    winner_index: Mapped[int] = mapped_column()  # blocks[1][0].common.winnerTeam
    finish_reason: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].common.finishReason, Have to discover what numbers mean
    duration_sec: Mapped[int] = mapped_column()  # blocks[1][0].common.duration
    team1_hp: Mapped[int] = mapped_column()  # blocks[1][0].common.teamHealth["1"]
    team2_hp: Mapped[int] = mapped_column()  # blocks[1][0].common.teamHealth["2"]
    replay_file: Mapped[str] = mapped_column(String(200))  # replay file name
    date_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )  # block[0].dateTime

    map_game: Mapped["MapGame"] = relationship(back_populates="games")
    entries: Mapped[list["PlayerEntry"]] = relationship(back_populates="game")


class PlayerEntry(Base):
    __tablename__ = "player_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))

    # Identity
    game_entity_id: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(50))  # blocks[1][1][entity_id].name
    team_index: Mapped[int] = mapped_column()  # blocks[1][1][entity_id].team

    # Vehicle
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))

    # Combat
    kills: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].kills
    damage_dealt: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageDealt
    sniper_damage_dealt: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].sniperDamageDealt
    damage_assisted_track: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageAssistedTrack
    damage_assisted_radio: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageAssistedRadio
    damage_assisted_stun: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageAssistedStun
    damage_assisted_smoke: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageAssistedSmoke
    damage_assisted_inspire: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageAssistedInspire
    max_hp: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].maxHealth
    damage_blocked_by_armor: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageBlockedByArmor
    damage_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageReceived
    potential_damage_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].potentialDamageReceived
    damage_received_from_invisibles: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].damageReceivedFromInvisibles
    end_game_hp: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].health
    spotted: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].spotted
    damaged: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].damaged
    stunned: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].stunned
    stun_duration: Mapped[float] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].stunDuration

    # Shots
    shots: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].shots
    direct_hits: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].directHits
    direct_enemy_hits: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].directEnemyHits
    direct_team_hits: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].directTeamHits
    direct_hits_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].directHitsReceived
    no_damage_direct_hits_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].noDamageDirectHitsReceived
    piercings: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].piercings
    piercing_enemy_hits: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].piercingEnemyHits
    piercings_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].piercingsReceived
    explosion_hits: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].explosionHits
    explosion_hits_received: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].explosionHitsReceived

    # Team damage
    is_team_killer: Mapped[bool] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].isTeamKiller
    team_kills: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].tkills
    team_damage_dealt: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].tdamageDealt
    team_destroyed_modules: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].tdestroyedModules

    # Survival
    survived: Mapped[bool] = mapped_column()  # blocks[1][1][entity_id].isAlive
    killed_by_entity: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # blocks[1][1].vehicles[entity_id].killerID
    death_reason: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].deathReason, -1 if not killed, gotta figure out what the other numbers mean
    is_first_blood: Mapped[bool] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].isFirstBlood
    mileage_m: Mapped[int] = mapped_column()  # blocks[1][0].vehicles[entity_id].mileage
    life_time_sec: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].lifeTime

    # Objectives
    capture_points: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].capturePoints
    dropped_capture_points: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].droppedCapturePoints
    vehicle_num_captured: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].vehicleNumCaptured

    # Mode-specific
    onslaught_role_skill_used: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].roleSkillUsed
    onslaught_health_repair: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].healthRepair
    onslaught_allied_health_repair: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].alliedHealthRepair
    onslaught_points_captured_by_own_team: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].poiCapturedByOwnTeam
    resource_absorbed: Mapped[int] = (
        mapped_column()
    )  # blocks[1][0].vehicles[entity_id].resourceAbsorbed
    # Have to chack if these last 2 columns are relevant for onslaught

    game: Mapped["Game"] = relationship(back_populates="entries")
    player: Mapped["Player"] = relationship(back_populates="entries")
    vehicle: Mapped["Vehicles"] = relationship(back_populates="entries")

    # blocks[1][0].vehicles[entity_id].entityCaptured ???
    # blocks[1][0].vehicles[entity_id].entityCaptured ???
