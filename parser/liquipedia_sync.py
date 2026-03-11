import os
import requests
import json
from dotenv import load_dotenv
from db.models import Match, Tournament, Team, Player, MapVeto, MapGame, MatchRoster
from db.database import SessionLocal

load_dotenv()

BASE_URL = "https://api.liquipedia.net/api/v3"
WIKI = "worldoftanks"
HEADERS = {
    "Authorization": f"Apikey {os.getenv('LIQUIPEDIA_API_KEY')}",
    "Accept-Encoding": "gzip",
    "User-Agent": "mammoth (WoTrank) (contact: mzielniok@proton.me)",
}


# HELPER FUNCTIONS


def _get(endpoint: str, params: dict) -> list:
    params.setdefault("wiki", WIKI)
    params.setdefault("limit", 200)
    params.setdefault("offset", 0)

    results = []
    while True:
        response = requests.get(
            f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params
        )
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(f"Liquipedia API error: {data['error']}")

        page = data.get("result", [])
        results.extend(page)

        if len(page) < params["limit"]:
            break
        params["offset"] += params["limit"]

    return results


REGION_TO_SERVER = {
    "Europe": "EU",
    "North America": "NA",
}


def _parse_location(item: dict) -> tuple[str, str]:
    locations = item.get("locations")
    tournament_type = item.get("type")

    if not locations:
        return None, None

    values = list(locations.values())

    if tournament_type.lower() == "offline":
        return ", ".join(values), "World"

    known_regions = [v for v in values if v in REGION_TO_SERVER]
    unknown_regions = [v for v in values if v not in REGION_TO_SERVER]

    region = ", ".join(known_regions + unknown_regions)

    if len(known_regions) > 1:
        server = "World"
    elif len(known_regions) == 1:
        server = REGION_TO_SERVER[known_regions[0]]
    else:
        server = "Unknown"

    return region, server


def _parse_mode(name: str, series: str) -> str:
    text = f"{name} {series or ''}".lower()
    if "onslaught" in text:
        return "Onslaught"
    elif "clan showdown" in text:
        return "Standard"
    else:
        return None


def _parse_round(bracket_data: dict) -> str:
    # Right now it works for brackets 4U4L1D and 8L4DS-2Q-U-8L2D-4QL
    coordinates = bracket_data.get("coordinates")
    if not coordinates:
        return None  # group stage / non-bracket match
    section = bracket_data.get("bracketsection")
    depth = int(coordinates.get("semanticDepth"))

    if depth == 0:
        return "Grand Final"
    elif depth == 1:
        return f"{section} Bracket Final"
    elif depth == 2:
        return f"{section} Bracket Semifinal"
    elif depth == 3:
        return f"{section} Bracket Quarterfinal"
    elif depth >= 4:
        return f"{section} Bracket Round {depth - 3}"
    else:
        return None


# UPSERT FUNCTIONS


def _upsert_teams(data: list, session) -> dict[str, Team]:
    """Collect all unique teams across all matches in the tournament, upsert them
    into the database, and find their liquipedia pages and IDs by name matching."""
    db_teams = {}
    for m in data:
        for opp in m.get("match2opponents", []):
            name = opp.get("name")

            if not name or name in db_teams:
                continue

            team = session.query(Team).filter_by(name=name).first()
            if not team:
                team = Team(
                    name=name,
                    template=opp.get("template"),
                )
                session.add(team)
                session.flush()
                print(f"  Added team: {team.name} (template: {team.template})")
            else:
                print(f"  Found existing team: {team.name} (template: {team.template})")

            db_teams[name] = team

    # Match teams to Liquipedia pages by name
    team_names = [team.name for team in db_teams.values() if team.name]

    if team_names:
        conditions = " OR ".join(f"[[name::{n}]]" for n in team_names)
        team_pages = _get(
            "team",
            {
                "conditions": conditions,
                "query": "pagename, pageid, name, template",
            },
        )

        teams_by_name = {t["name"]: t for t in team_pages}

        for team in db_teams.values():
            page = teams_by_name.get(team.name)
            if page:
                team.liquipedia_id = page["pageid"]
                team.template = page["template"]
                print(
                    f"  Updated team {team.name} with Liquipedia ID: {team.liquipedia_id}"
                )
            else:
                print(f"  No Liquipedia page found for team: {team.name}")

        session.flush()

    return db_teams


def _upsert_players(data: list, session) -> dict[str, Player]:
    """Collect all unique players across all matches in the tournament, upsert them
    into the database, and find their liquipedia pages and IDs by name matching."""
    db_players = {}
    for m in data:
        for opp in m.get("match2opponents", []):
            for p in opp.get("match2players", []):
                pagename = p.get("name")

                if not pagename or pagename in db_players:
                    continue

                player = session.query(Player).filter_by(pagename=pagename).first()
                if not player:
                    player = Player(
                        pagename=pagename,
                        name=p.get("displayname"),
                        nationality=p.get("flag"),
                    )
                    session.add(player)
                    session.flush()
                    print(f"  Added player: {player.name}")
                else:
                    print(f"  Found existing player: {player.name}")

                db_players[pagename] = player

    # Match players to Liquipedia pages by name
    player_names = [p.pagename for p in db_players.values() if p.pagename]

    if player_names:
        conditions = " OR ".join(f"[[pagename::{n}]]" for n in player_names)
        player_pages = _get(
            "player",
            {
                "conditions": conditions,
                "query": "pagename, pageid, id, alternateid, nationality",
            },
        )

        players_by_name = {p["pagename"]: p for p in player_pages}

        for player in db_players.values():
            page = players_by_name.get(player.pagename)
            if page:
                player.liquipedia_id = page["pageid"]
                player.name = page["id"]
                player.alternate_names = page["alternateid"]
                player.nationality = page["nationality"]
                print(
                    f"  Updated player {player.pagename} with Liquipedia ID: {player.liquipedia_id}"
                )
            else:
                print(f"  No Liquipedia page found for player: {player.pagename}")

        session.flush()

    return db_players


def _upsert_match(
    m: dict, tournament: Tournament, db_teams: dict, session
) -> Match | None:
    """Insert a single match. Returns None if it already exists."""
    if session.query(Match).filter_by(liquipedia_id=m["match2id"]).first():
        print(f"  Match already exists: {m['match2id']}")
        return None

    opp1, opp2 = m["match2opponents"]
    team1 = db_teams.get(opp1.get("name"))
    team2 = db_teams.get(opp2.get("name"))
    winner_idx = str(m.get("winner"))
    winner = team1 if winner_idx == "1" else team2 if winner_idx == "2" else None

    match = Match(
        tournament_id=tournament.id,
        liquipedia_id=m.get("match2id"),
        stage=m.get("section"),
        round=_parse_round(m.get("match2bracketdata", {})),
        best_of=m.get("bestof"),
        team1_id=team1.id if team1 else None,
        team1_score=opp1.get("score"),
        team2_id=team2.id if team2 else None,
        team2_score=opp2.get("score"),
        winner_id=winner.id if winner else None,
        date_time=m.get("date"),
    )
    session.add(match)
    session.flush()
    print(f"  Added match: {opp1.get('name')} vs {opp2.get('name')}")

    return match


def _upsert_match_roster(
    m: dict, match: Match, db_teams: dict, db_players: dict, session
) -> None:
    """Persist which players played for which team in this match."""
    opp1, opp2 = m["match2opponents"]
    for opp, team in [
        (opp1, db_teams.get(opp1.get("name"))),
        (opp2, db_teams.get(opp2.get("name"))),
    ]:
        if not team:
            continue
        for p in opp.get("match2players", []):
            player = db_players.get(p.get("name"))
            if not player:
                continue
            existing = (
                session.query(MatchRoster)
                .filter_by(match_id=match.id, player_id=player.id)
                .first()
            )
            if not existing:
                session.add(
                    MatchRoster(
                        match_id=match.id,
                        player_id=player.id,
                        team_id=team.id,
                    )
                )
    session.flush()


def _upsert_map_vetos(
    m: dict, match: Match, db_teams: dict, session
) -> dict[int, MapVeto]:
    """Insert map veto entries. Returns a dict keyed by veto order for MapGame linking."""
    veto_map = m.get("extradata", {}).get("mapveto", {})
    if not veto_map:
        return {}

    opp1, opp2 = m["match2opponents"]
    vetos_by_order: dict[int, MapVeto] = {}

    for order_str, veto in sorted(veto_map.items(), key=lambda x: int(x[0])):
        order = int(order_str)

        if "team1" in veto:
            map_name = veto["team1"]
            team = db_teams.get(opp1.get("name"))
        elif "team2" in veto:
            map_name = veto["team2"]
            team = db_teams.get(opp2.get("name"))
        elif "decider" in veto:
            map_name = veto["decider"]
            team = None  # decider has no owning team
        else:
            continue

        map_veto = MapVeto(
            match_id=match.id,
            team_id=team.id if team else None,
            map=map_name,
            type=veto.get("type"),  # "ban", "pick" or "decider"
            order=order,
        )
        session.add(map_veto)
        vetos_by_order[order] = map_veto

    session.flush()
    return vetos_by_order


def _upsert_map_games(
    m: dict, match: Match, vetos_by_order: dict[int, MapVeto], session
) -> None:
    """Insert map game entries, optionally linking to their corresponding map veto."""
    veto_by_map = {v.map: v for v in vetos_by_order.values()}

    for i, game in enumerate(m.get("match2games", []), start=1):
        scores = game.get("scores", [])
        winner_raw = game.get("winner")
        map_name = game.get("map") or ""

        map_game = MapGame(
            match_id=match.id,
            game_index=i,
            map=map_name,
            veto_id=veto_by_map[map_name].id if map_name in veto_by_map else None,
            team1_score=scores[0] if len(scores) > 0 else None,
            team2_score=scores[1] if len(scores) > 1 else None,
            winner_index=int(winner_raw) if winner_raw and winner_raw.strip() else None,
            result_type=game.get("resulttype") or None,
            vod_url=game.get("vod") or None,
        )
        session.add(map_game)

    session.flush()


# PARSER FUNCTIONS


def get_tournament(tournament_pagename: str, session) -> Tournament:
    data = _get(
        "tournament",
        {
            "conditions": f"[[pagename::{tournament_pagename}]]",
            "query": "pageid, name, seriespage, type, locations, format, startdate, enddate, liquipediatier",
        },
    )

    if not data:
        raise ValueError(f"Tournament not found: {tournament_pagename}")

    item = data[0]
    existing = session.query(Tournament).filter_by(liquipedia_id=item["pageid"]).first()
    if existing:
        print(f"  Tournament already exists: {existing.name}")
        return existing

    location, server = _parse_location(item)

    tournament = Tournament(
        liquipedia_id=item.get("pageid"),
        pagename=tournament_pagename,
        name=item.get("name"),
        series=item.get("seriespage"),
        type=item.get("type"),
        location=location,
        server=server,
        format=item.get("format"),
        mode=_parse_mode(item.get("name"), item.get("seriespage")),
        start_date=item.get("startdate"),
        end_date=item.get("enddate"),
        liquipedia_tier=item.get("liquipediatier"),
    )
    session.add(tournament)
    session.flush()
    print(f"Added tournament: {tournament.name}")
    return tournament


def get_matches(tournament: Tournament, session):
    data = _get(
        "match",
        {
            "conditions": f"[[pagename::{tournament.pagename}]]",
            "query": "match2id, match2bracketid, match2bracketdata, match2opponents, match2games, section, winner, bestof, date, extradata",
        },
    )

    print(json.dumps(data[-1], indent=2))

    data = [m for m in data if len(m.get("match2opponents", [])) == 2]

    db_teams = _upsert_teams(data, session)
    db_players = _upsert_players(data, session)

    for m in data:
        match = _upsert_match(m, tournament, db_teams, session)
        if match is None:
            continue

        _upsert_match_roster(m, match, db_teams, db_players, session)
        vetos_by_order = _upsert_map_vetos(m, match, db_teams, session)
        _upsert_map_games(m, match, vetos_by_order, session)


# Sync entry point


def sync_tournament(tournament_pagename: str):
    session = SessionLocal()
    try:
        tournament = get_tournament(tournament_pagename, session)
        get_matches(tournament, session)
        session.commit()
        print(f"Synchronized tournament: {tournament.name}")
    except Exception as e:
        session.rollback()
        print(f"Error occurred while synchronizing tournament: {e}")
        raise
    finally:
        session.close()
