"""Build every figure and print the tables used in the README.

Usage:
    python run.py              # uses data/statsbomb_passes.duckdb
    python run.py --rebuild    # re-download StatsBomb data first
"""
import argparse
from pathlib import Path

import pandas as pd

from src.database import build_database
from src.network import centralisation, centrality
from src.plots import (BLUE, ORANGE, hub_chart, pass_share_by_match, season_network,
                       side_by_side)
from src.queries import PassAnalysis

TEAM = "Bayer Leverkusen"
FIG = Path(__file__).parent / "figures"
pd.set_option("display.width", 160)


def match_panel(db, match_id, team, color, heading):
    nodes = db.run("04_match_nodes", match_id=match_id, team=team)
    edges = db.run("05_match_edges", match_id=match_id, team=team)
    cutoff = db.con.execute("SELECT cutoff_elapsed FROM first_change WHERE match_id=$m AND team=$t",
                            {"m": match_id, "t": team}).fetchall()[0][0]
    cent = centrality(nodes, edges)
    stats = {"team": team, "match_id": match_id, "minutes": round(cutoff / 60),
             "passes": int(edges["passes"].sum()),
             "centralisation": centralisation(nodes, edges),
             "top_3_pagerank": ", ".join(cent["player"].head(3))}
    sub = (f"{stats['passes']} completed open-play passes in the first {stats['minutes']} min · "
           f"centralisation {stats['centralisation']:.2f}")
    return {"nodes": nodes, "edges": edges, "color": color, "heading": heading,
            "subheading": sub}, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    if args.rebuild:
        build_database()
    db = PassAnalysis()
    FIG.mkdir(exist_ok=True)

    # 1-2. Season network and centrality
    nodes = db.run("06_season_nodes", team=TEAM, min_minutes=1800)
    edges = db.run("07_season_edges", team=TEAM)
    cent = centrality(nodes, edges)
    season_network(nodes, edges, cent, FIG / "season_network.png")
    hub_chart(cent, nodes, FIG / "who_the_ball_goes_through.png")
    print("Season profile (1,800+ minutes):")
    print(nodes.merge(cent, on="player")[["player", "minutes", "passes_made_p90", "progressive_p90",
                                          "involvement_pct", "betweenness", "pagerank"]]
          .round(2).to_string(index=False))
    print("\nTop passing pairs (season):")
    print(edges.head(6).round(1).to_string(index=False))

    # 3-4. The two Bayern games
    feb = db.match_id(TEAM, "Bayern Munich", "2024-02-10")
    sep = db.match_id(TEAM, "Bayern Munich", "2023-09-15")
    lev_feb, s1 = match_panel(db, feb, TEAM, BLUE, "Leverkusen")
    bay_feb, s2 = match_panel(db, feb, "Bayern Munich", ORANGE, "Bayern Munich")
    side_by_side([lev_feb, bay_feb], "Leverkusen 3–0 Bayern Munich, 10 February 2024",
                 "Bayern had 62% of the completed passes. Their most central players were "
                 "centre-backs Dier and Upamecano.", FIG / "leverkusen_bayern_3-0.png")
    lev_sep, s3 = match_panel(db, sep, TEAM, BLUE, "Away 2–2, 15 September 2023")
    lev_feb2 = dict(lev_feb, heading="Home 3–0, 10 February 2024")
    side_by_side([lev_sep, lev_feb2], "Leverkusen against Bayern: September vs February",
                 "Wirtz moved from the left wing to centre-forward, and the team's average passing "
                 "position was about 5 m deeper.",
                 FIG / "leverkusen_vs_bayern_sep_vs_feb.png")
    print("\nBayern games, networks up to first substitution:")
    print(pd.DataFrame([s3, s1, s2]).round(3).to_string(index=False))

    summary = db.run("08_match_summary")
    pass_share_by_match(summary, TEAM, feb,
                        "Lowest share of the season:\n3–0 vs Bayern (37.7%)",
                        FIG / "pass_share_by_match.png")
    lev = summary[summary["team"] == TEAM]
    print("\nLeverkusen match summary (season averages):")
    print(lev[["completed", "completion_pct", "pass_share_pct", "progressive",
               "goals", "goals_against", "xg"]].mean().round(1).to_string())
    print("\nLowest pass share games:")
    print(lev.nsmallest(5, "pass_share_pct")[["match_date", "opponent", "venue", "pass_share_pct",
                                              "goals", "goals_against", "xg"]]
          .round(1).to_string(index=False))


if __name__ == "__main__":
    main()
