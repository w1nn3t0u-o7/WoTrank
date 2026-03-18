<script lang="ts">
  import { onMount } from "svelte";
  import { fetchPlayers, fetchTournaments } from "$lib/api";

  type Tournament = {
    id: number;
    name: string;
  };

  type Player = {
    id: number;
    display_name: string | null;
    name: string | null;
    nationality: string | null;
    games_played: number;
    avg_damage: number | null;
    avg_kills: number | null;
    avg_assisted: number | null;
    avg_spotted: number | null;
    survival_rate: number | null;
  };

  let players = $state<Player[]>([]);
  let tournaments = $state<Tournament[]>([]);
  let selectedTournament = $state("");
  let sortBy = $state("avg_damage");

  const SORT_OPTIONS = [
    { value: "avg_damage",    label: "Avg Damage" },
    { value: "avg_kills",     label: "Avg Kills" },
    { value: "avg_assisted",  label: "Avg Assisted" },
    { value: "avg_spotted",   label: "Avg Spotted" },
    { value: "survival_rate", label: "Survival Rate" },
  ];

  async function load() {
    const params: Record<string, string> = { sort_by: sortBy };
    if (selectedTournament) params.tournament_id = selectedTournament;
    players = await fetchPlayers(params);
  }

  onMount(async () => {
    tournaments = await fetchTournaments();
    await load();
  });
</script>

<h1>Player Leaderboard</h1>

<div>
  <select bind:value={selectedTournament} onchange={load}>
    <option value="">All Tournaments</option>
    {#each tournaments as t}
      <option value={t.id}>{t.name}</option>
    {/each}
  </select>

  <select bind:value={sortBy} onchange={load}>
    {#each SORT_OPTIONS as opt}
      <option value={opt.value}>{opt.label}</option>
    {/each}
  </select>
</div>

<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Player</th>
      <th>Games</th>
      <th>Avg Dmg</th>
      <th>Avg Kills</th>
      <th>Avg Assisted</th>
      <th>Spotted</th>
      <th>Survival%</th>
    </tr>
  </thead>
  <tbody>
    {#each players as p, i}
      <tr>
        <td>{i + 1}</td>
        <td><a href="/players/{p.id}">{p.display_name ?? p.name}</a></td>
        <td>{p.games_played}</td>
        <td>{p.avg_damage?.toFixed(0)}</td>
        <td>{p.avg_kills?.toFixed(2)}</td>
        <td>{p.avg_assisted?.toFixed(0)}</td>
        <td>{p.avg_spotted?.toFixed(2)}</td>
        <td>{((p.survival_rate ?? 0) * 100).toFixed(1)}%</td>
      </tr>
    {/each}
  </tbody>
</table>


