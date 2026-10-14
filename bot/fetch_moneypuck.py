"""Download MoneyPuck's goalie season summary CSV and save it in data/moneypuck/.

Uses the CSV that MoneyPuck publishes on https://moneypuck.com/data.htm rather
than scraping goalies.htm: their terms allow the listed downloads for
non-commercial use with credit, and block unapproved scraping.
"""

import csv
import io
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

URL = "https://moneypuck.com/moneypuck/playerData/seasonSummary/{season}/regular/goalies.csv"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "moneypuck"
EASTERN = ZoneInfo("America/New_York")
CREDIT = "Data courtesy of MoneyPuck.com (https://moneypuck.com)"
REQUIRED_COLUMNS = {"name", "team", "situation", "games_played", "xGoals", "goals"}


def current_season(now: datetime) -> int:
    """MoneyPuck labels a season by its starting year; a new one starts in September."""
    return now.year if now.month >= 9 else now.year - 1


def download(season: int) -> str:
    req = urllib.request.Request(
        URL.format(season=season),
        headers={"User-Agent": "GoaltendingJournalBot/1.0 (daily, once per day)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def leaders(rows: list[dict], min_games: int = 3, top: int = 25) -> list[dict]:
    """Goals saved above expected (xGoals - goals) for all situations."""
    out = []
    for r in rows:
        if r["situation"] != "all":
            continue
        gp = int(float(r["games_played"] or 0))
        if gp < min_games:
            continue
        xg, ga = float(r["xGoals"]), float(r["goals"])
        out.append({
            "name": r["name"],
            "team": r["team"],
            "games_played": gp,
            "goals_against": int(ga),
            "xgoals_against": round(xg, 2),
            "gsax": round(xg - ga, 2),
        })
    return sorted(out, key=lambda g: g["gsax"], reverse=True)[:top]


def main() -> int:
    now = datetime.now(EASTERN)
    season = current_season(now)
    try:
        text = download(season)
    except urllib.error.HTTPError as e:
        print(f"MoneyPuck returned HTTP {e.code} for season {season}", file=sys.stderr)
        return 1

    rows = list(csv.DictReader(io.StringIO(text)))
    missing = REQUIRED_COLUMNS - set(rows[0].keys() if rows else [])
    if not rows or missing:
        print(f"Unexpected CSV shape (rows={len(rows)}, missing={sorted(missing)})", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"goalies_{season}.csv").write_text(text, encoding="utf-8")
    summary = {
        "season": f"{season}-{season + 1}",
        "fetched_at": now.isoformat(timespec="seconds"),
        "source": URL.format(season=season),
        "credit": CREDIT,
        "goalies": len({r["name"] for r in rows}),
        "gsax_leaders": leaders(rows),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rows)} rows for {summary['season']} ({summary['goalies']} goalies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
