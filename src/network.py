"""Network metrics (networkx) computed from the node and edge tables returned by sql/.

SQL builds the graph data; graph algorithms like betweenness and PageRank are easier in Python.
"""
import networkx as nx
import pandas as pd


def build_graph(nodes: pd.DataFrame, edges: pd.DataFrame) -> nx.Graph:
    """Undirected weighted graph. Weight = completed passes between the pair (both directions)."""
    keep = set(nodes["player"])
    g = nx.Graph()
    g.add_nodes_from(keep)
    for r in edges.itertuples():
        if r.player_a in keep and r.player_b in keep and r.player_a != r.player_b:
            # 'distance' is the inverse of weight, for shortest-path metrics:
            # a pair that passes a lot is "close" together
            g.add_edge(r.player_a, r.player_b, weight=r.passes, distance=1.0 / r.passes)
    return g


def centrality(nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    """Per-player centrality.

    - weighted_degree_pct: share of all passes in the network that involve the player
    - betweenness: how often the player sits on the strongest route between two teammates
      (the "connector")
    - pagerank: importance from being linked to other important players
    """
    g = build_graph(nodes, edges)
    total = sum(d["weight"] for _, _, d in g.edges(data=True))
    deg = dict(g.degree(weight="weight"))
    out = pd.DataFrame({
        "player": list(g.nodes),
        "weighted_degree_pct": [100 * deg[p] / (2 * total) for p in g.nodes],
        "betweenness": pd.Series(nx.betweenness_centrality(g, weight="distance", normalized=True)),
        "pagerank": pd.Series(nx.pagerank(g, weight="weight")),
    }).reset_index(drop=True)
    return out.sort_values("pagerank", ascending=False).reset_index(drop=True)


def centralisation(nodes: pd.DataFrame, edges: pd.DataFrame) -> float:
    """Freeman-style centralisation on weighted degree, 0 (everyone equal) to 1 (one hub)."""
    g = build_graph(nodes, edges)
    deg = pd.Series(dict(g.degree(weight="weight")), dtype=float)
    if deg.sum() == 0 or len(deg) < 3:
        return float("nan")
    share = deg / deg.sum()
    n = len(share)
    # max possible sum of differences is when one node has all the weight (star graph)
    star = pd.Series([0.5] + [0.5 / (n - 1)] * (n - 1))
    return float((share.max() - share).sum() / (star.max() - star).sum())
