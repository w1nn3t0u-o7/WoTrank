import json
import struct
import datetime
from pathlib import Path

MAGIC_NUM = b"\x12\x32\x34\x11"
OBSERVER_VEHICLE = "ussr:Observer"


def parse_replay_blocks(replay_path: str) -> list:
    blocks = []
    with open(replay_path, "rb") as f:
        if f.read(4) != MAGIC_NUM:
            raise ValueError(f"Not a valid WoT replay: {replay_path}")
        block_count = struct.unpack("I", f.read(4))[0]
        for i in range(block_count):
            size = struct.unpack("I", f.read(4))[0]
            try:
                blocks.append(json.loads(f.read(size)))
            except json.JSONDecodeError as e:
                raise ValueError(f"Block {i} JSON parse error: {e}")
    return blocks


def build_match(block0: dict, common: dict, arena_id: str, replay_file: str) -> dict:
    raw_date = block0.get("dateTime", "")
    try:
        dt = datetime.datetime.strptime(raw_date, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        dt = None

    return {
        "arena_unique_id":  arena_id,
        "replay_file":      replay_file,
        "date_time":        dt,
        "map_name":         block0.get("mapName"),
        "map_display_name": block0.get("mapDisplayName"),
        "gameplay_id":      block0.get("gameplayID"),
        "battle_type":      block0.get("battleType"),
        "bonus_type":       common.get("bonusType"),
        "duration_sec":     common.get("duration"),
        "winner_team":      common.get("winnerTeam"),
        "wot_version":      block0.get("clientVersionFromExe"),
        "server_name":      block0.get("serverName"),
        "recorder_name":    block0.get("playerName"),
        "recorder_id":      block0.get("playerID"),
        "source":           "replay",
    }


def build_player_entries(results: dict, roster: dict, frags_block: dict) -> list:
    vehicles = results.get("vehicles", {})  # entity_id → [perf_dict]
    players  = results.get("players", {})   # accountDBID(str) → {name, clan, team}

    entries = []

    for entity_id, vehicle_list in vehicles.items():
        if not vehicle_list:
            continue

        # Skip observer vehicles (present in some tournament replays)
        identity = roster.get(entity_id, {})
        if identity.get("vehicleType") == OBSERVER_VEHICLE:
            continue

        perf       = vehicle_list[0]
        account_id = str(perf.get("accountDBID", ""))
        player_id  = players.get(account_id, {})

        # Prefer roster for identity (end-of-battle state has deathInfo)
        name  = identity.get("name")  or player_id.get("name")
        clan  = identity.get("clanAbbrev") or player_id.get("clanAbbrev", "")
        team  = perf.get("team")

        # Vehicle
        veh_type   = identity.get("vehicleType", "")
        veh_parts  = veh_type.split(":") if ":" in veh_type else [veh_type, veh_type]

        # Survival & death
        alive      = bool(identity.get("isAlive", 1))
        death_info = identity.get("deathInfo") or {}
        killer_id  = str(death_info.get("killerID", "")) if death_info else None

        entries.append({
            "account_id":            int(account_id) if account_id else None,
            "name":                  name,
            "clan":                  clan,
            "team":                  team,
            "entity_id":             entity_id,
            "vehicle_type":          veh_type,
            "vehicle_nation":        veh_parts[0],
            "vehicle_tag":           veh_parts[1] if len(veh_parts) > 1 else veh_type,
            "kills":                 frags_block.get(entity_id, {}).get("frags"),
            "damage_dealt":          perf.get("damageDealt"),
            "damage_assisted_radio": perf.get("damageAssistedRadio"),
            "damage_assisted_track": perf.get("damageAssistedTrack"),
            "damage_assisted_stun":  perf.get("damageAssistedStun"),
            "damage_assisted_inspire":perf.get("damageAssistedInspire"),
            "damage_assisted_smoke": perf.get("damageAssistedSmoke"),
            "damage_blocked":        perf.get("damageBlockedByArmor"),
            "damage_received":       perf.get("damageReceived"),
            "spotted":               perf.get("spotted"),
            "shots":                 perf.get("shots"),
            "direct_hits":           perf.get("directHits"),
            "piercings":             perf.get("piercings"),
            "piercings_received":    perf.get("piercingsReceived"),
            "survived":              alive,
            "life_time_sec":         perf.get("lifeTime"),
            "death_reason":          perf.get("deathReason"),
            "killed_by_entity_id":   killer_id,
            "xp":                    perf.get("xp"),
            "credits":               perf.get("credits"),
            "source":                "replay",
        })

    return entries


def import_replay(replay_path: str, session) -> int:
    """
    Parse a .wotreplay file and insert match + player entries into DB.
    Returns the new match ID, or None if already imported (duplicate).
    """
    blocks  = parse_replay_blocks(replay_path)
    block0  = blocks[0]
    results = blocks[1][0]   # personal, players, vehicles, common, avatars
    roster  = blocks[1][1]   # entity_id → identity + deathInfo
    frags   = blocks[1][2]   # entity_id → { frags: N }

    arena_id = str(results.get("arenaUniqueID", ""))

    # Deduplication: skip if already imported
    existing = session.query(Match).filter_by(arena_unique_id=arena_id).first()
    if existing:
        print(f"  Already imported: arena {arena_id}")
        return None

    # Build and insert match
    match_data = build_match(block0, results["common"], arena_id, replay_path)
    match = Match(**match_data)
    session.add(match)
    session.flush()  # get match.id before inserting entries

    # Build and insert player entries
    entries = build_player_entries(results, roster, frags)
    for entry_data in entries:
        entry = PlayerEntry(match_id=match.id, **entry_data)
        session.add(entry)

    session.commit()
    print(f"  Imported match {match.id}: {match.map_display_name} "
          f"({len(entries)} players, winner team {match.winner_team})")
    return match.id