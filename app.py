"""Streamlit dashboard: Bayer Leverkusen 2023/24 passing networks.

Run locally:  streamlit run app.py
Data logic is in sql/ (DuckDB); network metrics in src/network.py; charts in src/interactive.py.
"""
import pandas as pd
import streamlit as st

from src import interactive as viz
from src.network import centralisation, centrality
from src.plots import short_name
from src.queries import PassAnalysis

TEAM = "Bayer Leverkusen"
st.set_page_config(page_title="Leverkusen 2023/24 · Passing networks", page_icon="⚽", layout="wide")


@st.cache_data
def query(name: str, **params) -> pd.DataFrame:
    # a fresh connection per cached query keeps DuckDB thread-safe under Streamlit
    return PassAnalysis().run(name, **params)


@st.cache_data
def cutoff_minute(match_id: int, team: str):
    db = PassAnalysis()
    r = db.con.execute("SELECT cutoff_elapsed FROM first_change WHERE match_id=$m AND team=$t",
                       {"m": match_id, "t": team}).fetchall()
    return round(r[0][0] / 60) if r else None


@st.cache_data
def sql_text(name: str) -> str:
    return PassAnalysis.sql(name)


# ---------- match list ----------
summary = query("08_match_summary")
lev = summary[summary["team"] == TEAM].sort_values("match_date").reset_index(drop=True)
lev["matchday"] = lev.index + 1
lev["result"] = lev.apply(lambda r: "W" if r.goals > r.goals_against
                          else ("D" if r.goals == r.goals_against else "L"), axis=1)
labels = {r.match_id: f"MD {r.matchday} · {r.match_date:%d %b %Y} · {r.result} {r.goals}–{r.goals_against} "
                      f"vs {r.opponent} ({r.venue})" for r in lev.itertuples()}
ids = list(labels)

# a click on the season chart sets a pending match; apply it before the selectbox is drawn
if "pending_match" in st.session_state:
    st.session_state["match_id"] = st.session_state.pop("pending_match")
if "match_id" not in st.session_state:
    st.session_state["match_id"] = int(lev.loc[lev["opponent"].eq("Bayern Munich")
                                               & lev["venue"].eq("H"), "match_id"].iloc[0])

st.title("Bayer Leverkusen 2023/24: passing networks")
st.caption("Every Bundesliga match of the unbeaten season · completed open-play passes · "
           "data: StatsBomb Open Data")

tab_match, tab_season = st.tabs(["Match explorer", "Season"])

# ======================= MATCH EXPLORER =======================
with tab_match:
    c1, c2, c3 = st.columns([3, 1.4, 1.2])
    match_id = c1.selectbox("Match", ids, format_func=labels.get, key="match_id")
    window = c2.radio("Network window", ["Until first substitution", "Full match"],
                      horizontal=True, help="Stopping at the first substitution keeps the same 11 "
                                            "players on the pitch, the standard approach.")
    min_passes = c3.slider("Min passes to draw a line", 1, 10, 3)
    full = window == "Full match"

    m = summary[summary["match_id"] == match_id]
    me = m[m["team"] == TEAM].iloc[0]
    opp = m[m["team"] != TEAM].iloc[0]

    k = st.columns(5)
    k[0].metric("Score", f"{me['goals']}–{me['goals_against']}",
                help=f"{TEAM} first; {'home' if me['venue'] == 'H' else 'away'}")
    k[1].metric("Leverkusen pass share", f"{me['pass_share_pct']:.0f}%",
                help="Share of the match's completed passes")
    k[2].metric("xG", f"{me['xg']:.2f} – {opp['xg']:.2f}")
    k[3].metric("Pass completion", f"{me['completion_pct']:.0f}% – {opp['completion_pct']:.0f}%")
    k[4].metric("Progressive passes", f"{int(me['progressive'])} – {int(opp['progressive'])}")

    tables = []
    cols = st.columns(2)
    for col, team, color in [(cols[0], TEAM, viz.BLUE), (cols[1], opp["team"], viz.ORANGE)]:
        nodes = query("04_match_nodes", match_id=match_id, team=team, full_match=full)
        edges = query("05_match_edges", match_id=match_id, team=team, full_match=full)
        cent = centrality(nodes, edges)
        cut = cutoff_minute(match_id, team)
        span = "full match" if full or cut is None else f"first {cut} min (until first sub)"
        with col:
            st.subheader("Leverkusen" if team == TEAM else team)
            st.plotly_chart(viz.network(nodes, edges, cent, color, min_passes), width="stretch",
                            config={"displayModeBar": False}, key=f"net_{team}")
            st.caption(f"{int(edges['passes'].sum())} completed open-play passes · {span} · "
                       f"centralisation {centralisation(nodes, edges):.2f} · most central: "
                       f"{short_name(cent['player'].iloc[0])}")
        t = nodes.merge(cent, on="player")[["player", "main_position", "passes_made",
                                            "passes_received", "pagerank", "betweenness"]]
        tables.append((team, t.sort_values("pagerank", ascending=False)))

    st.caption("Attacking left to right · node position = average location of passes made and "
               "received · node size = passes made + received · hover a player or a line for details")

    st.subheader("Who the ball went through")
    tcols = st.columns(2)
    for col, (team, t) in zip(tcols, tables):
        col.markdown(f"**{team}**")
        col.dataframe(
            t.rename(columns={"player": "Player", "main_position": "Position", "passes_made": "Made",
                              "passes_received": "Received", "pagerank": "PageRank",
                              "betweenness": "Betweenness"}),
            hide_index=True, width="stretch",
            column_config={"PageRank": st.column_config.NumberColumn(format="%.3f"),
                           "Betweenness": st.column_config.NumberColumn(format="%.2f")})

# ======================= SEASON =======================
with tab_season:
    st.subheader("Pass share, every league game")
    st.caption("Click a bar to load that match in the Match explorer tab.")
    event = st.plotly_chart(viz.pass_share_bars(lev, st.session_state["match_id"]), width="stretch",
                            config={"displayModeBar": False}, on_select="rerun",
                            selection_mode="points", key="share_chart")
    pts = (event or {}).get("selection", {}).get("points", []) if event else []
    if pts:
        clicked = int(pts[0]["customdata"][6])
        if clicked != st.session_state["match_id"]:
            st.session_state["pending_match"] = clicked
            st.rerun()

    st.subheader("Season passing network")
    s1, s2 = st.columns(2)
    min_minutes = s1.slider("Players with at least … league minutes", 900, 2700, 1800, step=300)
    season_min_passes = s2.slider("Min passes (season) to draw a line", 20, 200, 60, step=20)
    nodes = query("06_season_nodes", team=TEAM, min_minutes=min_minutes)
    edges = query("07_season_edges", team=TEAM)
    cent = centrality(nodes, edges)
    a, b = st.columns([1.6, 1])
    with a:
        st.plotly_chart(viz.network(nodes, edges, cent, viz.BLUE, season_min_passes, height=520),
                        width="stretch", config={"displayModeBar": False}, key="season_net")
        st.caption(f"{len(nodes)} players · completed open-play passes across all 34 matches")
    with b:
        st.plotly_chart(viz.hub_bars(cent), width="stretch", config={"displayModeBar": False},
                        key="hub")

    st.dataframe(
        nodes.merge(cent, on="player")[["player", "usual_position", "minutes", "passes_made_p90",
                                        "progressive_p90", "involvement_pct", "betweenness", "pagerank"]]
        .rename(columns={"player": "Player", "usual_position": "Usual position", "minutes": "Minutes",
                         "passes_made_p90": "Passes /90", "progressive_p90": "Progressive /90",
                         "involvement_pct": "Involvement %", "betweenness": "Betweenness",
                         "pagerank": "PageRank"}),
        hide_index=True, width="stretch",
        column_config={c: st.column_config.NumberColumn(format="%.2f")
                       for c in ["Passes /90", "Progressive /90", "Involvement %", "Betweenness", "PageRank"]})

    with st.expander("Method and the SQL behind this page"):
        st.markdown(
            "- **Open play** excludes corners, free kicks, throw-ins, goal kicks and kick-offs.\n"
            "- **Betweenness**: share of strongest routes between teammates that pass through a player.\n"
            "- **PageRank**: importance from being linked to other important players.\n"
            "- **Centralisation**: 0 = everyone equally involved, 1 = one player in everything.\n"
            "- **Involvement %**: share of the team's completed open-play passes a player made or received.")
        for name in ["03_first_substitution", "05_match_edges", "06_season_nodes"]:
            st.code(sql_text(name), language="sql")
