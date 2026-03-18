const BASE = "http://localhost:8000";

export async function fetchPlayers(params?: Record<string, string>) {
  const qs = params ? "?" + new URLSearchParams(params) : "";
  const res = await fetch(`${BASE}/players/${qs}`);
  return res.json();
}

export async function fetchPlayer(id: number) {
  return (await fetch(`${BASE}/players/${id}`)).json();
}

export async function fetchTournaments() {
  return (await fetch(`${BASE}/tournaments/`)).json();
}

export async function fetchTeam(id: number) {
  return (await fetch(`${BASE}/teams/${id}`)).json();
}

export async function fetchVehicleStats() {
  return (await fetch(`${BASE}/stats/vehicles`)).json();
}

export async function fetchMapStats() {
  return (await fetch(`${BASE}/stats/maps`)).json();
}
