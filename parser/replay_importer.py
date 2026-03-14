import json
import re
import struct
import datetime
from collections import Counter
from pathlib import Path
from difflib import SequenceMatcher

from db.models import MapGame, Match, Player, PlayerAccount, Game, MatchRoster, PlayerEntry, Vehicles

MAGIC_NUM = b"\x12\x32\x34\x11"
OBSERVER_TAG = "ussr:Observer"


def parse_replay_blocks(replay_path: str) -> list:
    blocks = []
    with open(replay_path, "rb") as replay:
        if replay.read(4) != MAGIC_NUM:
            raise ValueError(f"Not a valid WoT replay: {replay_path}")

        block_count = struct.unpack("I", replay.read(4))[0]

        for i in range(block_count):
            size = struct.unpack("I", replay.read(4))[0]
            try:
                blocks.append(json.loads(replay.read(size)))
            except json.JSONDecodeError as e:
                raise ValueError(f"Block {i} JSON parse error: {e}")
    return blocks


def resolve_players(roster: dict, vehicles: dict, session) -> dict[str, Player]:
    """Returns {entity_id: Player}. Tries account_id first, falls back to name.
    Writes new PlayerAccount rows when a name match reveals an unknown account."""

    account_id_map: dict[int, Player] = {
        row.account_id: row.player
        for row in session.query(PlayerAccount).join(PlayerAccount.player).all()
        if row.account_id is not None
    }

    matched: dict[str, Player] = {}
    new_accounts: list[PlayerAccount] = []

    for entity_id, identity in roster.items():
        if identity.get("vehicleType") == OBSERVER_TAG:
            continue

        perf_list = vehicles.get(entity_id)
        raw_account_id = perf_list[0].get("accountDBID") if perf_list else None
        account_id = int(raw_account_id) if raw_account_id else None

        if account_id and account_id in account_id_map:
            matched[entity_id] = account_id_map[account_id]
            continue

        replay_name = identity.get("name", "")
        player = _find_player_by_name(replay_name, session)

        if player:
            matched[entity_id] = player
            if account_id and account_id not in account_id_map:
                new_accounts.append(PlayerAccount(player_id=player.id, account_id=account_id,))
                account_id_map[account_id] = player
        else:
            print(f"  Warning: could not match player with name '{replay_name}' and account ID '{account_id}'")

    for account in new_accounts:
        session.add(account)

    return matched


_STRIP_SUFFIXES = re.compile(
    r'[_\-\.]?(eu|na|ru|as|sea|wr|wot|1|2|3|x|xx|_+)$',
    re.IGNORECASE
)

def _normalize(name: str) -> str:
    """Lowercase, strip common suffixes/underscores, unify l/I/1."""
    name = name.strip().lower()

    prev = None
    while prev != name:
        prev = name
        name = _STRIP_SUFFIXES.sub("", name)
    # Unify visually identical characters
    name = name.replace("l", "i").replace("1", "i")
    return name


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _find_player_by_name(name: str, session) -> Player | None:
    all_players = session.query(Player).all()
    norm_name = _normalize(name)

    # Pass 1 — exact match on primary name or alternate names
    for player in all_players:
        candidates = [player.name or "", player.display_name or "",] + [
            a.strip() for a in (player.alternate_names or "").split(",")
        ]
        if any(name == c for c in candidates):
            return player

    # Pass 2 — normalized exact match
    for player in all_players:
        candidates = [player.name or "", player.display_name or "",] + [
            a.strip() for a in (player.alternate_names or "").split(",")
        ]
        if any(norm_name == _normalize(c) for c in candidates):
            return player

    # Pass 3 — fuzzy match on normalized names (similarity threshold 0.82)
    best_player, best_score = None, 0.0
    for player in all_players:
        candidates = [player.name or "", player.display_name or "",] + [
            a.strip() for a in (player.alternate_names or "").split(",")
        ]
        for c in candidates:
            score = _similarity(norm_name, _normalize(c))
            if score > best_score:
                best_score = score
                best_player = player

    if best_score >= 0.82:
        print(f"  Fuzzy matched '{name}' → '{best_player.name}' (score: {best_score:.2f})")
        return best_player

    return None


def find_map_game(block0: dict, entity_to_player: dict[str, Player], session) -> MapGame | None:
    """Returns a MapGame matching the replay's map and game mode."""
    map_name = block0.get("mapDisplayName")
    raw_date = block0.get("dateTime", "")
    try:
        replay_dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        print(f"  Warning: could not parse replay date: '{raw_date}'")
        replay_dt = None

    known_players = list(entity_to_player.values())
    if not known_players:
        return None
    
    match_scores: Counter = Counter()
    for r in session.query(MatchRoster).filter(MatchRoster.player_id.in_([p.id for p in known_players])).all():
        match_scores[r.match_id] += 1

    if not match_scores:
        return None
    
    top_score = match_scores.most_common(1)[0][1]
    if top_score < 5:
        print(f"  Low roster overlap with known matches (max {top_score} players). Skipping map/game match.")
        return None
    
    top_matches = [m for m, score in match_scores.items() if score == top_score]

    if len(top_matches) == 1:
        best_match_id = top_matches[0]
    elif replay_dt is not None:
        candidates = session.Query(Match).filter(Match.id.in_(top_matches)).all()
        candidates_with_dt = [m for m in candidates if m.date_time is not None]
        if not candidates_with_dt:
            print(f"  No candidate matches with valid date. Skipping map/game match.")
            return None
        best_match = min(candidates_with_dt, key=lambda m: abs((m.date_time - replay_dt).total_seconds()))
        best_match_id = best_match.id
    else:
        print(f"  Multiple candidate matches with equal roster overlap and no replay date. Skipping map/game match.")
        return None
    
    return session.query(MapGame).filter_by(match_id=best_match_id, map=map_name).first()


def resolve_vehicle(vehicle_type_raw: str, session) -> Vehicles | None:
    if ":" not in vehicle_type_raw:
        return None
    _, tag = vehicle_type_raw.split(":", 1)
    return session.query(Vehicles).filter_by(tag=tag).first()


def build_game(
    block0: dict,
    common: dict,
    arena_id: str,
    map_game_id: int | None,
    replay_path: str,
) -> Game:
    raw_date = block0.get("dateTime", "")
    try:
        dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        dt = None

    team_health = common.get("teamHealth", {})

    return Game(
        map_game_id=map_game_id,
        arena_unique_id=str(arena_id),
        map=block0.get("mapDisplayName"),
        game_version=block0.get("clientVersionFromExe"),
        server=block0.get("serverName"),
        date_time=dt,
        winner_index=common.get("winnerTeam"),
        finish_reason=common.get("finishReason"),
        duration_sec=common.get("duration"),
        team1_hp=team_health.get("1"),
        team2_hp=team_health.get("2"),
        replay_file=Path(replay_path).name,
    )


def build_player_entries(
    game_id: int,
    vehicles: dict,
    roster: dict,
    entity_to_player: dict[str, Player],
    session,
) -> list[PlayerEntry]:
    entries = []

    for entity_id, perf_list in vehicles.items():
        if not perf_list:
            continue

        identity = roster.get(entity_id, {})
        if identity.get("vehicleType") == OBSERVER_TAG:
            continue

        perf = perf_list[0]
        player = entity_to_player.get(entity_id)

        # Vehicle FK
        vehicle_type_raw = identity.get("vehicleType", "")
        vehicle = resolve_vehicle(vehicle_type_raw, session)

        # Death info
        death_info = identity.get("deathInfo") or {}
        killer_id = str(death_info.get("killerID")) if death_info else None

        entries.append(PlayerEntry(
            game_id=game_id,
            player_id=player.id if player else None,

            # Identity
            game_entity_id=str(entity_id),
            name=identity.get("name"),
            team_index=perf.get("team"),

            # Vehicle
            vehicle_id=vehicle.id if vehicle else None,

            # Combat
            kills=perf.get("kills"),
            damage_dealt=perf.get("damageDealt"),
            sniper_damage_dealt=perf.get("sniperDamageDealt"),
            damage_assisted_track=perf.get("damageAssistedTrack"),
            damage_assisted_radio=perf.get("damageAssistedRadio"),
            damage_assisted_stun=perf.get("damageAssistedStun"),
            damage_assisted_smoke=perf.get("damageAssistedSmoke"),
            damage_assisted_inspire=perf.get("damageAssistedInspire"),
            max_hp=perf.get("maxHealth"),
            damage_blocked_by_armor=perf.get("damageBlockedByArmor"),
            damage_received=perf.get("damageReceived"),
            potential_damage_received=perf.get("potentialDamageReceived"),
            damage_received_from_invisibles=perf.get("damageReceivedFromInvisibles"),
            end_game_hp=perf.get("health"),
            spotted=perf.get("spotted"),
            damaged=perf.get("damaged"),
            stunned=perf.get("stunned"),
            stun_duration=perf.get("stunDuration"),

            # Shots
            shots=perf.get("shots"),
            direct_hits=perf.get("directHits"),
            direct_enemy_hits=perf.get("directEnemyHits"),
            direct_team_hits=perf.get("directTeamHits"),
            direct_hits_received=perf.get("directHitsReceived"),
            no_damage_direct_hits_received=perf.get("noDamageDirectHitsReceived"),
            piercings=perf.get("piercings"),
            piercing_enemy_hits=perf.get("piercingEnemyHits"),
            piercings_received=perf.get("piercingsReceived"),
            explosion_hits=perf.get("explosionHits"),
            explosion_hits_received=perf.get("explosionHitsReceived"),

            # Team damage
            is_team_killer=perf.get("isTeamKiller"),
            team_kills=perf.get("tkills"),
            team_damage_dealt=perf.get("tdamageDealt"),
            team_destroyed_modules=perf.get("tdestroyedModules"),

            # Survival
            survived=bool(identity.get("isAlive", 0)),
            killed_by_entity=killer_id,
            death_reason=perf.get("deathReason"),
            is_first_blood=perf.get("isFirstBlood"),
            mileage_m=perf.get("mileage"),
            life_time_sec=perf.get("lifeTime"),

            # Objectives
            capture_points=perf.get("capturePoints"),
            dropped_capture_points=perf.get("droppedCapturePoints"),
            vehicle_num_captured=perf.get("vehicleNumCaptured"),

            # Onslaught
            onslaught_role_skill_used=perf.get("roleSkillUsed"),
            onslaught_health_repair=perf.get("healthRepair"),
            onslaught_allied_health_repair=perf.get("alliedHealthRepair"),
            onslaught_points_captured_by_own_team=perf.get("poiCapturedByOwnTeam"),
            resource_absorbed=perf.get("resourceAbsorbed"),
        ))

    return entries


def import_replay(replay_path: str, session) -> int | None:
    blocks = parse_replay_blocks(replay_path)
    block0 = blocks[0]
    results = blocks[1][0]
    roster = blocks[1][1]

    arena_id = str(results.get("arenaUniqueID", ""))
    common = results.get("common", {})
    vehicles = results.get("vehicles", {})

    if session.query(Game).filter_by(arena_unique_id=arena_id).first():
        print(f"  Skipping duplicate replay with arenaUniqueID: {arena_id}")
        return None
    
    entity_to_player = resolve_players(roster, vehicles, session)
    map_game = find_map_game(block0, entity_to_player, session)

    if map_game is None:
        print(f"  No matching map/game found for replay. Importing with null map/game reference.")

    game = build_game(block0, common, arena_id, map_game.id if map_game else None, replay_path)
    session.add(game)
    session.flush()

    entries = build_player_entries(game.id, vehicles, roster, entity_to_player, session)
    for entry in entries:
        session.add(entry)

    session.commit()
    unmatched = [e for e in entries if e.player_id is None]
    print(
        f"  Imported game {game.id}: {game.map} | "
        f"{len(entries)} players ({len(unmatched)} unmatched) | "
        f"winner: team {game.winner_index}"
        + (f" → MapGame {map_game.id}" if map_game else " [UNLINKED]")
    )
    return game.id
