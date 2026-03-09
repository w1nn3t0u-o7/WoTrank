import os
import requests
import json
from dotenv import load_dotenv
from db.models import Tournament, Team, Player
from db.database import SessionLocal

load_dotenv()

BASE_URL = "https://api.liquipedia.net/api/v3"
WIKI = "worldoftanks"
HEADERS = {
    "Authorization": f"Apikey {os.getenv('LIQUIPEDIA_API_KEY')}",
    "Accept-Encoding": "gzip",
    "User-Agent": "mammoth (WoTrank) (contact: mzielniok@proton.me)"
}

# HELPER FUNCTIONS

def _get(endpoint: str, params: dict) -> list:
    params.setdefault("wiki", WIKI)
    params.setdefault("limit", 200)
    params.setdefault("offset", 0)

    results = []
    while True:
        response = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
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
    "Europe":        "EU",
    "North America":  "NA",
}

def _parse_location(item: dict) -> tuple[str, str]:
    locations = item.get("locations")
    tournament_type = item.get("type")

    if not locations:
        return None, None

    values = list(locations.values())

    if tournament_type.lower() == "offline":
        region = ", ".join(values)
        return region, "World"
    
    known_regions = [v for v in values if v in REGION_TO_SERVER]
    unknown_regions = [v for v in values if v not in REGION_TO_SERVER]

    all_regions = known_regions + unknown_regions
    region = ", ".join(all_regions)

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
    return None

# PARSER FUNCTIONS

def get_tournament(tournament_name: str, session) -> Tournament:

    data = _get("tournament", {
                "conditions": f"[[pagename::{tournament_name}]]",
                "query": "pageid, name, seriespage, type, locations, format, startdate, enddate, liquipediatier"
    })

    if not data:
        raise ValueError(f"Tournament not found: {tournament_name}")
    
    # print(json.dumps(data, indent=2))
    
    item = data[0]
    existing = session.query(Tournament).filter_by(liquipedia_id=item["pageid"]).first()
    if existing:
        print(f"  Tournament already exists: {existing.name}")
        return existing
    
    tournament = Tournament(
        liquipedia_id = item.get("pageid"),
        name = item.get("name"),
        series = item.get("seriespage"),
        type = item.get("type"),
        location = _parse_location(item)[0],
        server = _parse_location(item)[1],
        format = item.get("format"),
        mode = _parse_mode(item.get("name"), item.get("seriespage")),
        start_date = item.get("startdate"),
        end_date = item.get("enddate"),
        liquipedia_tier = item.get("liquipediatier")
    )

    session.add(tournament)
    session.flush()  # to get tournament.id for foreign keys
    print(f"Added tournament: {tournament.name}")
    return tournament

def get_matches(tournament_name: str, session):
    data = _get("match", {
        "conditions": f"[[pagename::{tournament_name}]]",
        "query": "match2id, match2bracketid, match2bracketdata, match2opponents",
    })

    print(json.dumps(data, indent=2))

    db_teams = {}
    db_players = {}

    for m in data:
        opponents = m.get("match2opponents", [])
        if len(opponents) != 2:
            print(f"  Skipping match {m.get('match2id')} with {len(opponents)} opponents")
            continue

        # Upsert teams
        for opp in opponents:
            team_name = opp.get("name")
            team_template = opp.get("template")

            if team_name in db_teams:
                continue

            team = session.query(Team).filter_by(name=team_name).first()
            if not team:
                team = Team(
                    template = team_template,
                    name = team_name,
                )

                session.add(team)
                session.flush()
                print(f"  Added team: {team.name} (template: {team.template})")
            else:
                print(f"  Found existing team: {team.name} (template: {team.template})")

            db_teams[team_name] = team

            players = opp.get("match2players", [])

            for p in players:
                player_name = p.get("name")
                if player_name in db_players:
                    continue

                player = session.query(Player).filter_by(page_name=player_name).first()
                if not player:
                    player = Player(
                        page_name = player_name,
                        name = p.get("displayname"),
                        nationality = p.get("flag"),
                    )

                    session.add(player)
                    session.flush()
                    print(f"    Added player: {player.name}")
                else:
                    print(f"    Found existing player: {player.name}")

                db_players[player_name] = player

    # Match teams to Liquipedia pages by name
    team_names = [team.name for team in db_teams.values() if team.name]

    if team_names:
        conditions = " OR ".join(f"[[name::{n}]]" for n in team_names)
        team_pages = _get("team", {
            "conditions": conditions,
            "query": "pagename, pageid, name, template",
        })

        # print(json.dumps(team_pages, indent=2))

        teams_by_name = {t["name"]: t for t in team_pages}

        for team in db_teams.values():
            page = teams_by_name.get(team.name)
            if page:
                team.liquipedia_id = page["pageid"]
                team.template = page["template"]
                print(f"  Updated team {team.name} with Liquipedia ID: {team.liquipedia_id}")
            else:
                print(f"  No Liquipedia page found for team: {team.name}")

        session.flush()

    # Match players to Liquipedia pages by name
    player_names = [player.page_name for player in db_players.values() if player.page_name]

    if player_names:
        conditions = " OR ".join(f"[[pagename::{n}]]" for n in player_names)
        player_pages = _get("player", {
            "conditions": conditions,
            "query": "pagename, pageid, id, alternateid, nationality",
        })

        # print(json.dumps(player_pages[:3], indent=2))

        players_by_name = {p["pagename"]: p for p in player_pages}

        for player in db_players.values():
            page = players_by_name.get(player.page_name)
            if page:
                player.liquipedia_id = page["pageid"]
                player.name = page["id"]
                player.alternate_names = page["alternateid"]
                player.nationality = page["nationality"]
                print(f"  Updated player {player.page_name} with Liquipedia ID: {player.liquipedia_id}")
            else:
                print(f"  No Liquipedia page found for player: {player.page_name}")

        session.flush()

def sync_tournament(tournament_name: str):
    session = SessionLocal()
    try:
        tournament = get_tournament(tournament_name, session)
        get_matches(tournament_name, session)
        session.commit()
        print(f"Synchronized tournament: {tournament.name}")
    except Exception as e:
        session.rollback()
        print(f"Error occurred while synchronizing tournament: {e}")
        raise
    finally:
        session.close()
