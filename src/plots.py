"""Figures. Every function takes DataFrames returned by sql/ (plus network metrics) and only draws."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#a3a29c"
GRID = "#e6e5e0"
BLUE = "#2a78d6"      # categorical slot 1 (Leverkusen)
ORANGE = "#eb6834"    # categorical slot 2 (opponent)
BLUE_RAMP = LinearSegmentedColormap.from_list("blue", ["#cfe0f6", "#2a78d6", "#0d3b73"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "text.color": INK,
    "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.edgecolor": MUTED, "font.size": 11,
})

SHORT = {"Alejandro Grimaldo García": "Grimaldo", "Piero Martín Hincapié Reyna": "Hincapié",
         "Victor Okoh Boniface": "Boniface", "Exequiel Alejandro Palacios": "Palacios",
         "Edmond Fayçal Tapsoba": "Tapsoba", "Dayotchanculle Upamecano": "Upamecano",
         "Min Jae Kim": "Kim Min-jae", "Eric Maxim Choupo-Moting": "Choupo-Moting"}


def short_name(name: str) -> str:
    return SHORT.get(name, name.split()[-1])


def _pitch():
    return Pitch(pitch_type="statsbomb", pitch_color=SURFACE, line_color=MUTED, linewidth=1,
                 line_zorder=1)


def draw_network(pitch, ax, nodes, edges, color=BLUE, min_passes=3, node_values=None,
                 size_col="involvement", max_node=1600, max_width=14):
    """Draw one passing network.

    nodes: player, x, y, <size_col>; edges: player_a, player_b, passes.
    node_values (optional Series indexed by player, 0-1) shades nodes on the blue ramp.
    """
    pos = nodes.set_index("player")[["x", "y"]]
    e = edges[(edges["passes"] >= min_passes)
              & edges["player_a"].isin(pos.index) & edges["player_b"].isin(pos.index)
              & (edges["player_a"] != edges["player_b"])].copy()
    wmax = e["passes"].max()
    for r in e.sort_values("passes").itertuples():
        a, b = pos.loc[r.player_a], pos.loc[r.player_b]
        frac = r.passes / wmax
        pitch.lines(a.x, a.y, b.x, b.y, ax=ax, lw=0.5 + max_width * frac,
                    color=color if node_values is None else "#2a78d6",
                    alpha=0.12 + 0.55 * frac, zorder=2)
    sizes = 120 + max_node * nodes[size_col] / nodes[size_col].max()
    if node_values is None:
        fc = color
    else:
        fc = [BLUE_RAMP(v) for v in node_values.reindex(nodes["player"]).fillna(0)]
    pitch.scatter(nodes["x"], nodes["y"], s=sizes, color=fc, edgecolors=SURFACE,
                  linewidths=2, ax=ax, zorder=3)
    # labels start just below each node, then get nudged apart where players overlap
    texts = []
    for r, sz in zip(nodes.itertuples(), sizes):
        radius = np.sqrt(sz) / 2 / 72 * ax.figure.dpi          # node radius in pixels
        dy = ax.transData.inverted().transform((0, 0))[1] - \
            ax.transData.inverted().transform((0, radius + 6))[1]
        texts.append(ax.text(r.x, r.y + abs(dy), short_name(r.player), ha="center", va="top",
                             fontsize=9, color=INK, zorder=5,
                             bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none",
                                       alpha=0.85)))
    adjust_text(texts, ax=ax, only_move={"text": "xy"}, expand=(1.15, 1.3),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))


def season_network(nodes, edges, cent, path, min_passes=60):
    pitch = _pitch()
    fig, ax = pitch.draw(figsize=(12, 9.2))
    fig.subplots_adjust(top=0.84, bottom=0.1)
    pr = cent.set_index("player")["pagerank"]
    shade = (pr - pr.min()) / (pr.max() - pr.min())
    draw_network(pitch, ax, nodes, edges, min_passes=min_passes, node_values=shade,
                 size_col="involvement_pct", max_node=2200, max_width=16)
    fig.text(0.05, 0.95, "Bayer Leverkusen 2023/24: season passing network",
             fontsize=18, weight="bold")
    fig.text(0.05, 0.915, "The 11 players with 1,800+ league minutes · completed open-play passes "
             f"· lines shown for pairs with {min_passes}+ passes",
             fontsize=11, color=INK_2)
    fig.text(0.05, 0.055, "Node position = average location of passes made and received · "
             "size = share of team passes involved in · darker = more central (PageRank)",
             fontsize=9, color=INK_2)
    fig.text(0.05, 0.03, "Attacking left to right · Data: StatsBomb Open Data",
             fontsize=9, color=INK_2)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def side_by_side(panels, title, subtitle, path, min_passes=3):
    """panels: list of dicts with nodes, edges, color, heading, subheading."""
    pitch = _pitch()
    fig, axs = pitch.grid(ncols=len(panels), figheight=8.2, grid_height=0.70, grid_width=0.96,
                          title_height=0.08, title_space=0.10, endnote_height=0.04,
                          endnote_space=0.02, space=0.04, axis=False)
    for ax, p in zip(np.atleast_1d(axs["pitch"]), panels):
        draw_network(pitch, ax, p["nodes"], p["edges"], color=p["color"], min_passes=min_passes)
        ax.text(0, 1.075, p["heading"], transform=ax.transAxes, fontsize=14, weight="bold",
                color=INK)
        ax.text(0, 1.025, p["subheading"], transform=ax.transAxes, fontsize=10, color=INK_2)
    t = axs["title"]
    t.text(0, 0.75, title, fontsize=18, weight="bold", va="center")
    t.text(0, 0.2, subtitle, fontsize=11, color=INK_2, va="center")
    e = axs["endnote"]
    e.text(0, 0.5, f"Completed open-play passes up to each team's first substitution · lines "
           f"for pairs with {min_passes}+ passes · node size = passes made + received · "
           "both teams attack left to right", fontsize=9, color=INK_2, va="center")
    e.text(1, 0.5, "Data: StatsBomb Open Data", fontsize=9, color=INK_2, ha="right", va="center")
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def pass_share_by_match(summary, team, highlight_match_id, note, path):
    """Bar per matchday: team's share of completed passes, one match highlighted."""
    d = summary[summary["team"] == team].sort_values("match_date").reset_index(drop=True)
    d["matchday"] = d.index + 1
    colors = [BLUE if m == highlight_match_id else "#b9c9dd" for m in d["match_id"]]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(d["matchday"], d["pass_share_pct"], color=colors, width=0.78, zorder=2)
    ax.hlines(50, 0.3, 34.5, color=MUTED, lw=1, ls="--", zorder=1)
    ax.text(34.6, 50, "50%", va="center", fontsize=9, color=INK_2)
    avg = d["pass_share_pct"].mean()
    ax.hlines(avg, 0.3, 34.5, color=INK_2, lw=1, zorder=1)
    ax.text(34.6, avg, f"season avg\n{avg:.0f}%", va="center", fontsize=9, color=INK_2)
    h = d[d["match_id"] == highlight_match_id].iloc[0]
    ax.annotate(note, xy=(h["matchday"], h["pass_share_pct"]),
                xytext=(h["matchday"] - 9.5, 22), fontsize=10, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlim(0.3, 37)
    ax.set_ylim(0, 100)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30, 34])
    ax.set_xlabel("Bundesliga matchday")
    ax.set_ylabel("Share of completed passes (%)")
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"{team}: share of the match's completed passes, every league game",
                 loc="left", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def hub_chart(cent, nodes, path):
    """Horizontal bars: share of network passes each player is involved in, hub highlighted."""
    d = cent.merge(nodes[["player", "passes_made_p90"]], on="player")
    d = d.sort_values("weighted_degree_pct")
    top = d["weighted_degree_pct"].idxmax()
    fig, ax = plt.subplots(figsize=(10, 5.6))
    colors = [BLUE if i == top else "#b9c9dd" for i in d.index]
    ax.barh(d["player"].map(short_name), d["weighted_degree_pct"], color=colors, height=0.7, zorder=2)
    for y, (v, b) in enumerate(zip(d["weighted_degree_pct"], d["betweenness"])):
        ax.text(v + 0.3, y, f"{v:.1f}%" + (f"   betweenness {b:.2f}" if b >= 0.1 else ""),
                va="center", fontsize=9, color=INK_2)
    ax.set_xlabel("Share of passes between the 11 regulars that involve the player (%)")
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, d["weighted_degree_pct"].max() * 1.45)
    ax.set_title("Who the ball goes through", loc="left", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
