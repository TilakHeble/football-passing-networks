"""Interactive Plotly charts for the Streamlit dashboard (app.py).

Inputs are the DataFrames returned by sql/ plus network metrics from src/network.py;
these functions only draw.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.plots import short_name

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#a3a29c"
GRID = "#e6e5e0"
BLUE = "#2a78d6"      # categorical slot 1 (Leverkusen)
ORANGE = "#eb6834"    # categorical slot 2 (opponent)
LIGHT_BLUE = "#b9c9dd"
FONT = dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=INK, size=13)


def _layout(fig, height, **kw):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font=FONT, showlegend=False,
        hoverlabel=dict(bgcolor="white", bordercolor=MUTED, font=dict(color=INK, size=12)), **kw)
    return fig


def _pitch_shapes():
    """Full StatsBomb pitch (120 x 80). The y axis is reversed so y=0 is the top touchline."""
    line = dict(color=MUTED, width=1)
    r = lambda x0, x1, y0, y1: dict(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, line=line, layer="below")
    shapes = [r(0, 120, 0, 80), r(0, 18, 18, 62), r(102, 120, 18, 62), r(0, 6, 30, 50), r(114, 120, 30, 50),
              dict(type="line", x0=60, x1=60, y0=0, y1=80, line=line, layer="below"),
              dict(type="circle", x0=50, x1=70, y0=30, y1=50, line=line, layer="below")]
    t = np.linspace(0, 2 * np.pi, 200)
    for spot, keep in [(12, lambda x: x > 18), (108, lambda x: x < 102)]:     # the two "D"s
        ax_, ay_ = spot + 10 * np.cos(t), 40 + 10 * np.sin(t)
        m = keep(ax_)
        # split into a contiguous run so the path doesn't jump across the circle
        pts = sorted(zip(ay_[m], ax_[m]))
        path = "M " + " L ".join(f"{x:.2f},{y:.2f}" for y, x in pts)
        shapes.append(dict(type="path", path=path, line=line, layer="below"))
    return shapes


def network(nodes: pd.DataFrame, edges: pd.DataFrame, cent: pd.DataFrame, color: str,
            min_passes: int = 3, height: int = 460) -> go.Figure:
    """Passing network on a full pitch, attacking left to right.

    nodes: 04_match_nodes / 06_season_nodes; edges: 05_match_edges / 07_season_edges;
    cent: src.network.centrality(nodes, edges).
    """
    fig = go.Figure()
    pos = nodes.set_index("player")[["x", "y"]]
    e = edges[(edges["passes"] >= min_passes) & edges["player_a"].isin(pos.index)
              & edges["player_b"].isin(pos.index) & (edges["player_a"] != edges["player_b"])]
    wmax = max(e["passes"].max(), 1) if len(e) else 1
    for r in e.sort_values("passes").itertuples():
        a, b = pos.loc[r.player_a], pos.loc[r.player_b]
        frac = r.passes / wmax
        fig.add_trace(go.Scatter(
            x=[a.x, b.x], y=[a.y, b.y], mode="lines", opacity=0.15 + 0.55 * frac,
            line=dict(color=color, width=0.8 + 12 * frac), hoverinfo="skip"))
        # an invisible midpoint marker gives each line a hover label
        fig.add_trace(go.Scatter(
            x=[(a.x + b.x) / 2], y=[(a.y + b.y) / 2], mode="markers",
            marker=dict(size=10, color="rgba(0,0,0,0)"),
            hovertemplate=f"<b>{short_name(r.player_a)} ↔ {short_name(r.player_b)}</b><br>"
                          f"{r.passes} completed passes<extra></extra>"))

    n = nodes.merge(cent, on="player", how="left")
    size_col = "involvement" if "involvement" in n else "involvement_pct"
    sizes = 14 + 34 * n[size_col] / n[size_col].max()
    made = n["passes_made"].astype(int)
    received = n["passes_received"].astype(int)
    pos_col = "main_position" if "main_position" in n else "usual_position"
    custom = np.stack([n["player"], n[pos_col].fillna(""), made, received,
                       n["pagerank"].fillna(0), n["betweenness"].fillna(0)], axis=-1)
    fig.add_trace(go.Scatter(
        x=n["x"], y=n["y"], mode="markers+text", text=n["player"].map(short_name),
        textposition="bottom center", textfont=dict(size=11, color=INK),
        marker=dict(size=sizes, color=color, line=dict(color=SURFACE, width=2)),
        customdata=custom,
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                      "Passes made %{customdata[2]} · received %{customdata[3]}<br>"
                      "PageRank %{customdata[4]:.3f} · betweenness %{customdata[5]:.2f}<extra></extra>"))
    fig.update_xaxes(range=[-2, 122], visible=False, fixedrange=True)
    fig.update_yaxes(range=[82, -2], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)
    fig.update_layout(shapes=_pitch_shapes())
    return _layout(fig, height)


def pass_share_bars(lev: pd.DataFrame, selected_match_id: int | None = None) -> go.Figure:
    """Leverkusen's share of completed passes per matchday; click a bar to open that match."""
    d = lev.sort_values("match_date").reset_index(drop=True)
    d["matchday"] = d.index + 1
    res = np.where(d["goals"] > d["goals_against"], "W", np.where(d["goals"] == d["goals_against"], "D", "L"))
    colors = [BLUE if m == selected_match_id else LIGHT_BLUE for m in d["match_id"]]
    custom = np.stack([d["opponent"], d["venue"], d["goals"], d["goals_against"], res,
                       d["match_date"].astype(str), d["match_id"]], axis=-1)
    fig = go.Figure(go.Bar(
        x=d["matchday"], y=d["pass_share_pct"], marker_color=colors, customdata=custom,
        hovertemplate="<b>MD %{x}: %{customdata[4]} %{customdata[2]}–%{customdata[3]} vs "
                      "%{customdata[0]} (%{customdata[1]})</b><br>%{customdata[5]}<br>"
                      "Pass share %{y:.1f}%<extra>click to open</extra>"))
    avg = d["pass_share_pct"].mean()
    fig.add_hline(y=50, line=dict(color=MUTED, dash="dash", width=1))
    fig.add_hline(y=avg, line=dict(color=INK_2, width=1),
                  annotation_text=f"season avg {avg:.0f}%", annotation_position="top left",
                  annotation_font=dict(color=INK_2, size=11))
    fig.update_xaxes(title="Matchday", tickvals=[1, 5, 10, 15, 20, 25, 30, 34], showgrid=False,
                     tickfont=dict(color=INK_2))
    fig.update_yaxes(title="Share of completed passes (%)", range=[0, 100], gridcolor=GRID,
                     tickfont=dict(color=INK_2))
    return _layout(fig, 360, clickmode="event+select")


def hub_bars(cent: pd.DataFrame) -> go.Figure:
    d = cent.sort_values("weighted_degree_pct")
    top = d["weighted_degree_pct"].max()
    fig = go.Figure(go.Bar(
        y=d["player"].map(short_name), x=d["weighted_degree_pct"], orientation="h",
        marker_color=[BLUE if v == top else LIGHT_BLUE for v in d["weighted_degree_pct"]],
        customdata=np.stack([d["player"], d["betweenness"], d["pagerank"]], axis=-1),
        text=d["weighted_degree_pct"].map("{:.1f}%".format), textposition="outside",
        textfont=dict(color=INK_2, size=11),
        hovertemplate="<b>%{customdata[0]}</b><br>%{x:.1f}% of network passes<br>"
                      "betweenness %{customdata[1]:.2f} · PageRank %{customdata[2]:.3f}<extra></extra>"))
    fig.update_xaxes(title="Share of passes between the regulars involving the player (%)",
                     gridcolor=GRID, range=[0, top * 1.25], tickfont=dict(color=INK_2))
    fig.update_yaxes(tickfont=dict(color=INK))
    return _layout(fig, 400)
