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
    params.setdefault("limit", 100)
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
    
    print(json.dumps(data, indent=2))
    
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

def get_teams_and_players(tournament_name: str, session):
    data = _get("placement", {
        "conditions": f"[[pagename::{tournament_name}]]",
        "query": "opponentname, opponenttemplate, opponenttype, opponentplayers", 
    })

    print(json.dumps(data, indent=2))

    placements = [p for p in data if p.get("opponenttype") == "team"]

    teams = _get("team", {
        "conditions": " OR ".join(f"[[pagename::{p['opponentname'].replace(' ', '_')}]]" for p in placements),
        "query": "pageid, pagename, name",
    })

    print(json.dumps(teams, indent=2))

    for p in placements:
        team = Team(
            liquipedia_id = next((t["pageid"] for t in teams if t["pagename"] == p["opponentname"].replace(" ", "_")), None),
            name = p.get("opponentname"),
        )
        session.add(team)
        
    session.flush()
    print(f"Added {len(placements)} teams")



def sync_tournament(tournament_name: str):
    session = SessionLocal()
    try:
        tournament = get_tournament(tournament_name, session)
        session.commit()
        print(f"Synchronized tournament: {tournament.name}")
    except Exception as e:
        session.rollback()
        print(f"Error occurred while synchronizing tournament: {e}")
        raise
    finally:
        session.close()
