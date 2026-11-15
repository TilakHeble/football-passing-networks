"""Build a DuckDB database of passes from StatsBomb Open Data.

Tables in data/statsbomb_passes.duckdb:
  matches      one row per match
  passes       every pass (both teams), with start/end location, recipient and outcome
  appearances  one row per player position stint (from lineups): on/off clock times, reasons
  clock        end-of-half clock per match, used to compute minutes played
  shots        every shot (player, team, xG, goal flag): match context
"""
from pathlib import Path
import warnings

import duckdb
import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore", module="statsbombpy")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "statsbomb_passes.duckdb"


def _clock(s):
    """'68:47' -> seconds on StatsBomb's match clock (second half starts at 45:00)."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    m, sec = s.split(":")
    return int(m) * 60 + int(sec)


def build_database(competition_id: int = 9, season_id: int = 281, db_path: Path = DB_PATH) -> Path:
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    matches = matches[["match_id", "match_date", "home_team", "away_team",
                       "home_score", "away_score"]].copy()
    matches["match_date"] = pd.to_datetime(matches["match_date"]).dt.date

    passes, apps, clocks, shots = [], [], [], []
    for match_id in matches["match_id"]:
        ev = sb.events(match_id=match_id)
        ev["clock"] = ev["minute"] * 60 + ev["second"]
        clocks.append({"match_id": match_id,
                       "h1_end": int(ev.loc[ev["period"] == 1, "clock"].max()),
                       "h2_end": int(ev.loc[ev["period"] == 2, "clock"].max())})

        p = ev[ev["type"] == "Pass"]
        get = lambda col: p[col] if col in p else pd.Series(index=p.index, dtype=object)
        passes.append(pd.DataFrame({
            "pass_id": p["id"], "match_id": match_id, "period": p["period"],
            "minute": p["minute"], "second": p["second"], "clock": p["clock"],
            "possession": p["possession"], "team": p["team"], "player": p["player"],
            "position": p["position"], "recipient": p["pass_recipient"],
            "x": p["location"].str[0], "y": p["location"].str[1],
            "end_x": p["pass_end_location"].str[0], "end_y": p["pass_end_location"].str[1],
            "outcome": p["pass_outcome"],            # NULL = completed
            "pass_type": p["pass_type"], "height": p["pass_height"],
            "length": p["pass_length"], "body_part": p["pass_body_part"],
            "play_pattern": p["play_pattern"],
            "under_pressure": get("under_pressure").fillna(False).astype(bool),
            "is_cross": get("pass_cross").fillna(False).astype(bool),
            "is_switch": get("pass_switch").fillna(False).astype(bool),
            "is_through_ball": get("pass_through_ball").fillna(False).astype(bool),
            "is_shot_assist": get("pass_shot_assist").fillna(False).astype(bool),
            "is_goal_assist": get("pass_goal_assist").fillna(False).astype(bool),
        }))

        s = ev[ev["type"] == "Shot"]
        shots.append(pd.DataFrame({"match_id": match_id, "team": s["team"], "player": s["player"],
                                   "xg": s["shot_statsbomb_xg"],
                                   "is_goal": s["shot_outcome"].eq("Goal"),
                                   "is_penalty": s["shot_type"].eq("Penalty")}))

        for team, lu in sb.lineups(match_id=match_id).items():
            for _, r in lu.iterrows():
                for pos in r["positions"]:
                    apps.append({
                        "match_id": match_id, "team": team, "player": r["player_name"],
                        "jersey_number": r["jersey_number"], "position": pos["position"],
                        "from_clock": _clock(pos["from"]), "to_clock": _clock(pos["to"]),
                        "from_period": pos["from_period"], "to_period": pos["to_period"],
                        "start_reason": pos["start_reason"], "end_reason": pos["end_reason"],
                    })

    tables = {"matches": matches, "passes": pd.concat(passes, ignore_index=True),
              "appearances": pd.DataFrame(apps), "clock": pd.DataFrame(clocks),
              "shots": pd.concat(shots, ignore_index=True)}
    db_path.parent.mkdir(exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        for name, df in tables.items():
            con.register("tmp_df", df)
            con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
    return db_path


def connect(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    if not db_path.exists():
        print("Database not found - downloading StatsBomb data (a couple of minutes)...")
        build_database(db_path=db_path)
    return duckdb.connect(str(db_path), read_only=True)


if __name__ == "__main__":
    print(f"Built {build_database()}")
