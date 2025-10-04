import re
from typing import Dict, List

import requests

API_BASE = "https://liquipedia.net/worldoftanks/api.php"
HEADERS = {"User-Agent": "WoTrank (mik.ziel7890@gmail.com)"}


def api_call(action: str, params: Dict[str, str]) -> Dict:
    params.update({"action": action, "format": "json"})
    response = requests.get(API_BASE, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return data


def get_tournament_list() -> List[str]:
    params = {
        "list": "categorymembers",
        "cmtitle": "Category:Tournaments",
        "cmtype": "page",
        "cmlimit": "max",
        "cmprop": "title",
    }
    data = api_call("query", params)
    return [page["title"] for page in data["query"]["categorymembers"]]


print(get_tournament_list())
