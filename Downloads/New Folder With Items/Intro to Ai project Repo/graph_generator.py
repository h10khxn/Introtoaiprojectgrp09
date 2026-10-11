"""
graph_generator.py — SOFE 3720 Group 9
Lead: Hamdan Khan (Environment & Graph Modeling)

Provides:
  - OTU_CAMPUS  : hardcoded real 12-node OTU campus graph
  - generate_graph(n, density, seed) : synthetic Euclidean graph generator
  - save_graph / load_graph          : JSON I/O your teammates can import
  - visualize_graph                  : matplotlib visualizer
  - generate_all_test_graphs()       : builds the full test suite (12–25 nodes)

Usage (by teammates):
    from graph_generator import load_graph, get_heuristic

    graph = load_graph("graphs/graph_20_medium.json")
    # graph["adjacency"][node] -> {neighbor: weight, ...}
    # graph["positions"][node] -> (x, y)   <- for Euclidean heuristic
    h = get_heuristic(graph, goal_node)
    dist = h(current_node)
"""

import math
import random
import json
import os

# ---------------------------------------------------------------------------
# REAL OTU CAMPUS GRAPH (12 nodes)
# Nodes: real buildings on OTU Founders Drive North campus
# Coordinates: approximate (x, y) in metres from a top-left origin
# Edges: actual walkable paths between adjacent buildings
# ---------------------------------------------------------------------------

OTU_CAMPUS = {
    "name": "otu_campus_real",
    "n_nodes": 12,
    "nodes": {
        "0":  {"x": 150,  "y": 60,   "label": "U5 Building"},
        "1":  {"x": 0,    "y": 310,  "label": "OPG Engineering"},
        "2":  {"x": 460,  "y": 40,   "label": "Shawenjigewinng Hall"},
        "3":  {"x": 310,  "y": 295,  "label": "Library"},
        "4":  {"x": 580,  "y": 290,  "label": "Energy Research Ctr"},
        "5":  {"x": 790,  "y": 390,  "label": "Business & IT"},
        "6":  {"x": 190,  "y": 620,  "label": "Justice Wing"},
        "7":  {"x": 40,   "y": 800,  "label": "Rec & Wellness"},
        "8":  {"x": 530,  "y": 665,  "label": "Science Building"},
        "9":  {"x": 750,  "y": 940,  "label": "Main Entrance"},
        "10": {"x": 680,  "y": 130,  "label": "SIRC"},
        "11": {"x": 920,  "y": 580,  "label": "Campus Field House"},
    },
    "edges": [
        [0, 2], [0, 1], [0, 3],
        [2, 10], [2, 3], [2, 4],
        [1, 3], [1, 6],
        [3, 4], [3, 6], [3, 8],
        [4, 5], [4, 8], [4, 10],
        [5, 11], [5, 9],
        [6, 7], [6, 8],
        [8, 9], [8, 11],
        [9, 11],
    ]
}

def _campus_to_adj(campus):
    """Convert OTU_CAMPUS edge list to weighted adjacency dict."""
    nodes = campus["nodes"]
    adj = {int(k): {} for k in nodes}
    for a, b in campus["edges"]:
        xa, ya = nodes[str(a)]["x"], nodes[str(a)]["y"]
        xb, yb = nodes[str(b)]["x"], nodes[str(b)]["y"]
        dist = round(math.sqrt((xa-xb)**2 + (ya-yb)**2), 2)
        adj[a][b] = dist
        adj[b][a] = dist
    return adj

# ---------------------------------------------------------------------------
# SYNTHETIC GRAPH GENERATOR
# ---------------------------------------------------------------------------

DENSITY_RADIUS_MULTIPLIER = {
    "sparse": 1.3,   # avg degree ~2–3
    "medium": 1.8,   # avg degree ~4–5
    "dense":  2.5,   # avg degree ~6–8
}

def _euclidean(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def _ensure_connected(positions, adj):
    """BFS from node 0; bridge any unreachable nodes to their nearest visited."""
    n = len(positions)
    visited = set()
    stack = [0]
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            stack.extend(adj[node].keys())

    for node in range(n):
        if node not in visited:
            nearest = min(visited,
                key=lambda j: _euclidean(positions[node], positions[j]))
            dist = round(_euclidean(positions[node], positions[nearest]), 2)
            adj[node][nearest] = dist
            adj[nearest][node] = dist
            visited.add(node)

    return adj

def generate_graph(n_nodes, density="medium", seed=42, area=1000):
    """
    Generate a random Euclidean graph.

    Parameters
    ----------
    n_nodes  : int   — number of nodes (12–50 recommended)
    density  : str   — "sparse" | "medium" | "dense"
    seed     : int   — random seed (fix for reproducibility)
    area     : int   — bounding box side length in metres

    Returns
    -------
    positions : dict  {node_id: (x, y)}
    adj       : dict  {node_id: {neighbor_id: weight, ...}}
    """
    random.seed(seed)
    multiplier = DENSITY_RADIUS_MULTIPLIER.get(density, 1.8)
    radius = (area / math.sqrt(n_nodes)) * multiplier

    # Place nodes with a minimum spacing to avoid clumping
    min_spacing = area / (n_nodes * 1.5)
    positions = {}
    attempts = 0
    while len(positions) < n_nodes and attempts < n_nodes * 200:
        x = random.uniform(50, area - 50)
        y = random.uniform(50, area - 50)
        if all(_euclidean((x, y), p) >= min_spacing for p in positions.values()):
            positions[len(positions)] = (round(x, 1), round(y, 1))
        attempts += 1

    # Fill remaining (if spacing too strict) without the spacing constraint
    while len(positions) < n_nodes:
        positions[len(positions)] = (
            round(random.uniform(50, area - 50), 1),
            round(random.uniform(50, area - 50), 1)
        )

    # Build adjacency from proximity radius
    adj = {i: {} for i in range(n_nodes)}
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            dist = _euclidean(positions[i], positions[j])
            if dist <= radius:
                adj[i][j] = round(dist, 2)
                adj[j][i] = round(dist, 2)

    # Guarantee full connectivity
    adj = _ensure_connected(positions, adj)

    return positions, adj

# ---------------------------------------------------------------------------
# SERIALISATION
# ---------------------------------------------------------------------------

def _build_graph_dict(name, positions, adj):
    return {
        "name": name,
        "n_nodes": len(positions),
        "positions": {str(i): list(pos) for i, pos in positions.items()},
        "adjacency": {
            str(i): {str(j): w for j, w in neighbors.items()}
            for i, neighbors in adj.items()
        }
    }

def save_graph(graph_dict, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(graph_dict, f, indent=2)
    n = graph_dict["n_nodes"]
    edge_count = sum(len(v) for v in graph_dict["adjacency"].values()) // 2
    print(f"  Saved {path}  ({n} nodes, {edge_count} edges)")

def load_graph(path):
    """
    Load a graph JSON file. Returns a dict with:
      graph["n_nodes"]              -> int
      graph["positions"][node_str]  -> [x, y]
      graph["adjacency"][node_str]  -> {neighbor_str: weight}
    """
    with open(path) as f:
        data = json.load(f)
    return data

# ---------------------------------------------------------------------------
# HEURISTIC FACTORY  (for teammates' A* / Greedy)
# ---------------------------------------------------------------------------

def get_heuristic(graph, goal_node):
    """
    Returns a callable h(node) = Euclidean distance from node to goal.
    Node IDs are strings (match the JSON keys).

    Example:
        h = get_heuristic(graph, "7")
        cost = h("3")   # straight-line distance from node 3 to node 7
    """
    gx, gy = graph["positions"][str(goal_node)]
    def h(node):
        nx, ny = graph["positions"][str(node)]
        return math.sqrt((nx - gx)**2 + (ny - gy)**2)
    return h

# ---------------------------------------------------------------------------
# VISUALISER
# ---------------------------------------------------------------------------

def visualize_graph(graph_dict, title=None, ax=None, save_path=None):
    """
    Draw the graph using matplotlib. Works for both real and synthetic graphs.
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    positions = graph_dict["positions"]
    adjacency = graph_dict["adjacency"]
    name = graph_dict.get("name", "graph")
    nodes = graph_dict.get("nodes", {})  # labels, only in OTU real graph

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(8, 7))

    ax.set_facecolor("#F0F4FA")

    # Draw edges
    drawn = set()
    for i_str, neighbors in adjacency.items():
        xi, yi = positions[i_str]
        for j_str, w in neighbors.items():
            key = tuple(sorted((i_str, j_str)))
            if key in drawn:
                continue
            drawn.add(key)
            xj, yj = positions[j_str]
            ax.plot([xi, xj], [yi, yj], color="#8BAFD4", lw=1.2, zorder=1)
            # Edge weight label at midpoint
            mx, my = (xi+xj)/2, (yi+yj)/2
            ax.text(mx, my, f"{w:.0f}", fontsize=5.5, ha="center",
                    color="#4A5568", zorder=2)

    # Draw nodes
    for i_str, (x, y) in positions.items():
        label = nodes.get(i_str, {}).get("label", i_str) if nodes else i_str
        ax.scatter(x, y, s=220, color="#00539C", edgecolors="#F0A500",
                   linewidths=1.8, zorder=3)
        ax.text(x, y, label, fontsize=6.5, ha="center", va="center",
                color="white", fontweight="bold", zorder=4)

    n = graph_dict["n_nodes"]
    edge_count = len(drawn)
    ax.set_title(title or name, fontsize=12, fontweight="bold", color="#00539C")
    ax.set_xlabel(f"{n} nodes · {edge_count} edges", fontsize=9, color="#4A5568")
    ax.axis("equal")
    ax.axis("off")

    if save_path and standalone:
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Visualized → {save_path}")
    elif standalone:
        plt.tight_layout()
        plt.show()

# ---------------------------------------------------------------------------
# GENERATE FULL TEST SUITE
# ---------------------------------------------------------------------------

def generate_all_test_graphs(out_dir="graphs"):
    """
    Generates the complete set of test graphs for the project.

    Graph sizes: 12, 15, 20, 25 nodes
    Densities  : sparse, medium, dense   (matches test conditions in proposal)
    Seeds      : fixed per size for reproducibility

    Also saves the real OTU campus graph.
    """
    os.makedirs(out_dir, exist_ok=True)
    generated = []

    # 1. Real OTU campus graph
    pos_otu = {int(k): (v["x"], v["y"]) for k, v in OTU_CAMPUS["nodes"].items()}
    adj_otu = _campus_to_adj(OTU_CAMPUS)
    d = _build_graph_dict("otu_campus_real", pos_otu, adj_otu)
    d["nodes"] = OTU_CAMPUS["nodes"]   # preserve building labels
    path = os.path.join(out_dir, "graph_otu_real.json")
    save_graph(d, path)
    generated.append((d, path, "OTU Campus (Real, 12 nodes)"))

    # 2. Synthetic graphs
    configs = [
        (12, "sparse",  42),
        (12, "medium",  42),
        (12, "dense",   42),
        (15, "sparse",  7),
        (15, "medium",  7),
        (15, "dense",   7),
        (20, "sparse",  13),
        (20, "medium",  13),
        (20, "dense",   13),
        (25, "sparse",  99),
        (25, "medium",  99),
        (25, "dense",   99),
    ]

    for n, density, seed in configs:
        pos, adj = generate_graph(n, density=density, seed=seed)
        name = f"graph_{n}_{density}"
        d = _build_graph_dict(name, pos, adj)
        path = os.path.join(out_dir, f"{name}.json")
        save_graph(d, path)
        generated.append((d, path, f"{n} nodes · {density}"))

    return generated

# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

def validate_graph(graph_dict):
    """
    Checks:
      1. All nodes have positions
      2. Graph is fully connected (BFS from node 0)
      3. All edge weights are positive
      4. Adjacency is symmetric
    Returns list of issues (empty = pass).
    """
    positions = graph_dict["positions"]
    adjacency = graph_dict["adjacency"]
    issues = []

    # Connectivity check
    visited = set()
    stack = [list(adjacency.keys())[0]]
    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            stack.extend(adjacency[node].keys())
    if len(visited) < len(adjacency):
        issues.append(f"NOT CONNECTED: only {len(visited)}/{len(adjacency)} nodes reachable")

    # Symmetry and positive weights
    for i, neighbors in adjacency.items():
        for j, w in neighbors.items():
            if w <= 0:
                issues.append(f"Non-positive weight on edge ({i},{j}): {w}")
            if i not in adjacency.get(j, {}):
                issues.append(f"Asymmetric edge: ({i},{j}) exists but ({j},{i}) missing")
            if i not in positions:
                issues.append(f"Node {i} has no position")

    return issues

# ---------------------------------------------------------------------------
# MAIN — run this file directly to generate all graphs
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import matplotlib.pyplot as plt

    SCRATCHPAD = os.path.dirname(os.path.abspath(__file__))
    GRAPH_DIR  = os.path.join(SCRATCHPAD, "graphs")
    VIZ_DIR    = os.path.join(SCRATCHPAD, "graph_images")
    os.makedirs(VIZ_DIR, exist_ok=True)

    print("=== Generating test graphs ===")
    generated = generate_all_test_graphs(out_dir=GRAPH_DIR)

    print("\n=== Validating ===")
    all_pass = True
    for gdict, path, label in generated:
        issues = validate_graph(gdict)
        status = "PASS" if not issues else f"FAIL: {issues}"
        print(f"  [{status}] {label}")
        if issues:
            all_pass = False

    print("\n=== Rendering visualizations ===")
    # Grid plot: 1 real + 12 synthetic (4 sizes × 3 densities)
    fig, axes = plt.subplots(4, 4, figsize=(20, 18))
    fig.suptitle("SOFE 3720 Group 9 — Test Graph Suite", fontsize=15,
                 fontweight="bold", color="#00539C")

    for idx, (gdict, path, label) in enumerate(generated):
        row, col = divmod(idx, 4)
        if row < 4 and col < 4:
            visualize_graph(gdict, title=label, ax=axes[row][col])

    # Hide any unused axes
    for i in range(len(generated), 16):
        r, c = divmod(i, 4)
        axes[r][c].set_visible(False)

    plt.tight_layout()
    grid_path = os.path.join(VIZ_DIR, "all_graphs.png")
    plt.savefig(grid_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved grid → {grid_path}")

    print(f"\n{'All validations passed!' if all_pass else 'Some validations FAILED — check above.'}")
    print(f"Graphs saved to: {GRAPH_DIR}")
    print(f"Images saved to: {VIZ_DIR}")
