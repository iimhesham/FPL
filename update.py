"""Fetches FPL data and writes data/data.json. No dependencies."""
import json, os, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = "https://fantasy.premierleague.com/api/"
HORIZON = 6


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "Mozilla/5.0 (fpl-picker)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    boot = get("bootstrap-static/")
    fixtures = get("fixtures/")
    events = boot["events"]
    cur = next((e for e in events if e["is_current"]), None)
    nxt = next((e for e in events if e["is_next"]), None)
    start = (nxt or cur)["id"]
    gws = [g for g in range(start, start + HORIZON) if g <= 38]

    teams = {t["id"]: {"n": t["name"], "s": t["short_name"]} for t in boot["teams"]}

    fx = {tid: [] for tid in teams}
    for f in fixtures:
        g = f.get("event")
        if g in gws:
            fx[f["team_h"]].append([g, teams[f["team_a"]]["s"], 1, f["team_h_difficulty"]])
            fx[f["team_a"]].append([g, teams[f["team_h"]]["s"], 0, f["team_a_difficulty"]])

    players = []
    for e in boot["elements"]:
        if e["status"] == "u":
            continue
        players.append({
            "id": e["id"], "n": e["web_name"], "t": e["team"], "p": e["element_type"],
            "c": e["now_cost"] / 10, "f": float(e["form"]), "pts": e["total_points"],
            "s": float(e["selected_by_percent"]), "st": e["status"], "nw": e["news"],
        })

    my = None
    team_id = int(os.environ.get("TEAM_ID") or json.load(open("config.json")).get("team_id") or 0)
    if team_id:
        try:
            entry = get(f"entry/{team_id}/")
            for ev in [nxt, cur]:
                if not ev:
                    continue
                try:
                    pk = get(f"entry/{team_id}/event/{ev['id']}/picks/")
                except urllib.error.HTTPError:
                    continue
                my = {
                    "name": entry.get("name"), "gw": ev["id"],
                    "picks": [p["element"] for p in pk["picks"]],
                    "bank": pk["entry_history"]["bank"], "value": pk["entry_history"]["value"],
                }
                break
        except Exception as ex:  # keep the rest of the data even if the team lookup fails
            print("team lookup failed:", ex)

    os.makedirs("data", exist_ok=True)
    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "gw": start, "gws": gws, "teams": teams, "fixtures": fx, "players": players, "my": my,
    }
    with open("data/data.json", "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("ok:", len(players), "players, team:", bool(my))


if __name__ == "__main__":
    main()
