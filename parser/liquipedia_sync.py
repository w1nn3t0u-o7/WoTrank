import os
import requests
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

def get_tournament(tournament_name: str, session) -> Tournament:

    data = _get("tournament", {"conditions": f"[[pagename::{tournament_name}]]",
                               "query": "pageid, pagename, name, startdate, enddate"
    })

    if not data:
        raise ValueError(f"Tournament not found: {tournament_name}")
    
    item = data[0]
    existing = session.query(Tournament).filter_by(liquipedia_id=item["pageid"]).first()
    if existing:
        print(f"  Tournament already exists: {existing.name}")
        return existing
    
    tournament = Tournament(
        name=item["name"],
        liquipedia_id=item["pageid"],
        start_date=item.get("startdate"),
        end_date=item.get("enddate"),
    )
    session.add(tournament)
    session.flush()  # to get tournament.id for foreign keys
    print(f"Added tournament: {tournament.name}")
    return tournament

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
