import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from db.models import Tournament, Team, Player, Match
from db.database import SessionLocal

load_dotenv()

BASE_URL = "https://api.liquipedia.net/api/v3"
WIKI     = "worldoftanks"
HEADERS  = {
    "Authorization": f"Apikey {os.getenv('LIQUIPEDIA_API_KEY')}",
    "Accept-Encoding": "gzip",
}


def _get(endpoint: str, params: dict) -> list:
    """Generic paginated GET — handles limit/offset automatically."""
    params.setdefault("wiki", WIKI)
    params.setdefault("limit", 1000)
    params.setdefault("offset", 0)

    results = []
    while True:
        resp = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise ValueError(f"Liquipedia API error: {data['error']}")

        batch = data.get("result", [])
        results.extend(batch)

        if len(batch) < params["limit"]:
            break   # no more pages
        params["offset"] += params["limit"]

    return results


def sync_tournament(tournament_name: str, session) -> Tournament:
    """
    Fetch one tournament by name and upsert into DB.
    tournament_name should match the Liquipedia pagename, e.g.
    'Onslaught_Legends_Cup/3'
    """
    data = _get("tournament", {
        "conditions": f"[[pagename::{tournament_name}]]",
        "query": "pagename,name,startdate,enddate",
    })

    if not data:
        raise ValueError(f"Tournament not found: {tournament_name}")

    t = data[0]
    existing = session.query(Tournament).filter_by(liquipedia_id=t["pagename"]).first()
    if existing:
        print(f"  Tournament already exists: {t['name']}")
        return existing

    tournament = Tournament(
        liquipedia_id = t["pagename"],
        name          = t.get("name") or tournament_name,
        start_date    = _parse_date(t.get("startdate")),
        end_date      = _parse_date(t.get("enddate")),
    )
    session.add(tournament)
    session.flush()
    print(f"  ✓ Tournament: {tournament.name}")
    return tournament


def sync_teams(tournament_name: str, session) -> dict:
    """
    Fetch all teams that participated in a tournament.
    Returns dict of liquipedia_id → Team for use in sync_players.
    """
    data = _get("team", {
        "conditions": f"[[pagename::_ROLLINGTEAMS_]] OR [[tournament::{tournament_name}]]",
        "query": "pagename,name,extradata",
    })

    # Fallback: fetch teams via placements in this tournament
    if not data:
        data = _get("placement", {
            "conditions": f"[[tournament::{tournament_name}]]",
            "query": "opponentname,opponenttemplate",
        })

    team_map = {}
    for t in data:
        lid = t.get("pagename") or t.get("opponenttemplate")
        if not lid:
            continue
        existing = session.query(Team).filter_by(liquipedia_id=lid).first()
        if not existing:
            existing = Team(
                liquipedia_id = lid,
                name          = t.get("name") or t.get("opponentname", lid),
                clan_tag      = t.get("extradata", {}).get("clantag") if isinstance(t.get("extradata"), dict) else None,
            )
            session.add(existing)
            session.flush()
            print(f"  ✓ Team: {existing.name}")
        team_map[lid] = existing

    return team_map


def sync_players(tournament_name: str, team_map: dict, session):
    """
    Fetch squad players for each team and upsert into players table.
    """
    data = _get("squadplayer", {
        "conditions": f"[[tournament::{tournament_name}]] AND [[status::active]]",
        "query": "pagename,id,name,team,extradata",
    })

    for p in data:
        lid = p.get("id") or p.get("pagename")
        if not lid:
            continue
        existing = session.query(Player).filter_by(liquipedia_id=lid).first()
        if existing:
            continue

        team_lid = p.get("team")
        team     = team_map.get(team_lid)

        player = Player(
            liquipedia_id = lid,
            name          = p.get("id") or p.get("name", lid),
            team_id       = team.id if team else None,
        )
        session.add(player)
        print(f"  ✓ Player: {player.name} ({team_lid})")

    session.flush()


def sync_matches(tournament_name: str, tournament: Tournament, session):
    """
    Fetch all matches for a tournament and upsert into matches table.
    """
    data = _get("match", {
        "conditions": f"[[tournament::{tournament_name}]]",
        "query": "pagename,match2id,date,opponent1,opponent2,winner,extradata,bestof",
    })

    for m in data:
        lid = m.get("match2id") or m.get("pagename")
        if not lid:
            continue
        existing = session.query(Match).filter_by(liquipedia_id=lid).first()
        if existing:
            continue

        # Resolve team FKs by name/template
        team1 = _find_team(m.get("opponent1"), session)
        team2 = _find_team(m.get("opponent2"), session)
        winner_num = m.get("winner")
        winner = team1 if winner_num == "1" else team2 if winner_num == "2" else None

        match = Match(
            liquipedia_id  = lid,
            tournament_id  = tournament.id,
            team1_id       = team1.id if team1 else None,
            team2_id       = team2.id if team2 else None,
            winner_team_id = winner.id if winner else None,
            date           = _parse_date(m.get("date")),
            stage          = m.get("extradata", {}).get("stagename") if isinstance(m.get("extradata"), dict) else None,
        )
        session.add(match)
        print(f"  ✓ Match: {m.get('opponent1')} vs {m.get('opponent2')}")

    session.flush()


def sync_all(tournament_name: str):
    """
    Full sync for one tournament. Run this for each tournament you want to add.
    """
    session = SessionLocal()
    try:
        print(f"\nSyncing tournament: {tournament_name}")
        tournament = sync_tournament(tournament_name, session)
        team_map   = sync_teams(tournament_name, session)
        sync_players(tournament_name, team_map, session)
        sync_matches(tournament_name, tournament, session)
        session.commit()
        print(f"\n✓ Sync complete for {tournament_name}")
    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        session.close()


# ── Helpers ────────────────────────────────────────────────

def _parse_date(value: str) -> datetime:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _find_team(name: str, session) -> Team:
    if not name:
        return None
    return session.query(Team).filter(
        (Team.liquipedia_id == name) | (Team.name == name) | (Team.clan_tag == name)
    ).first()
