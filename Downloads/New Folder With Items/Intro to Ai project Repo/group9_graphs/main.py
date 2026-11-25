import json
import math
import heapq
import time
import sys


def load_graph(filepath):
    """Loads raw JSON graph dataset."""
    with open(filepath, 'r') as f:
        return json.load(f)


def euclidean_distance(coord1, coord2):
    """Calculates straight-line heuristic distance between two points."""
    x1, y1 = coord1
    x2, y2 = coord2
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)


def build_normalized_graph(graph):
    """Normalizes JSON graph format into standard adjacency lists and coordinates."""
    raw_nodes = graph.get("nodes", {})
    raw_positions = graph.get("positions", {})
    raw_adj = graph.get("adjacency", {})
    raw_edges = graph.get("edges") or graph.get("links") or []

    node_ids = set()
    if isinstance(raw_nodes, dict):
        node_ids.update(str(k) for k in raw_nodes.keys())
    elif isinstance(raw_nodes, list):
        node_ids.update(str(n.get("id", n)) if isinstance(n, dict) else str(n) for n in raw_nodes)

    if isinstance(raw_positions, dict):
        node_ids.update(str(k) for k in raw_positions.keys())
    if isinstance(raw_adj, dict):
        node_ids.update(str(k) for k in raw_adj.keys())

    positions = {}
    for nid in node_ids:
        pos = (0.0, 0.0)
        if isinstance(raw_positions, dict) and nid in raw_positions:
            val = raw_positions[nid]
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                pos = (float(val[0]), float(val[1]))
            elif isinstance(val, dict):
                pos = (float(val.get("x", 0.0)), float(val.get("y", 0.0)))
        elif isinstance(raw_nodes, dict) and nid in raw_nodes:
            ndata = raw_nodes[nid]
            if isinstance(ndata, dict):
                if "pos" in ndata:
                    pos = tuple(ndata["pos"])
                elif "x" in ndata and "y" in ndata:
                    pos = (float(ndata["x"]), float(ndata["y"]))
        positions[nid] = pos

    adj = {nid: [] for nid in node_ids}

    if isinstance(raw_adj, dict):
        for u, neighbors in raw_adj.items():
            u_str = str(u)
            if u_str not in adj:
                adj[u_str] = []

            if isinstance(neighbors, dict):
                for v, edge_data in neighbors.items():
                    v_str = str(v)
                    w = float(edge_data.get("weight", edge_data.get("cost", 1.0))) if isinstance(edge_data, dict) else float(edge_data)
                    adj[u_str].append((v_str, w))

            elif isinstance(neighbors, list):
                for item in neighbors:
                    if isinstance(item, dict):
                        v_str = str(item.get("node", item.get("v", item.get("to", ""))))
                        w = float(item.get("weight", item.get("cost", 1.0)))
                    else:
                        v_str = str(item)
                        w = 1.0
                    if v_str:
                        adj[u_str].append((v_str, w))

    if not any(adj.values()) and raw_edges:
        for edge in raw_edges:
            u = str(edge.get("u", edge.get("source", edge.get("from", ""))))
            v = str(edge.get("v", edge.get("target", edge.get("to", ""))))
            w = float(edge.get("weight", edge.get("cost", 1.0)))
            if u in adj and v in adj:
                adj[u].append((v, w))
                adj[v].append((u, w))

    return list(node_ids), positions, adj


def uniform_cost_search(node_ids, adj, start_node, goal_node):
    start_time = time.perf_counter()
    open_set = []
    heapq.heappush(open_set, (0, start_node))
    g_score = {node: float('inf') for node in node_ids}
    g_score[start_node] = 0
    came_from = {}
    explored_sequence = []

    while open_set:
        current_g, current = heapq.heappop(open_set)

        if current not in explored_sequence:
            explored_sequence.append(current)

        if current == goal_node:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            exec_time = (time.perf_counter() - start_time) * 1000
            return path, g_score[goal_node], len(explored_sequence), exec_time, explored_sequence

        if current_g > g_score[current]:
            continue

        for neighbor, weight in adj.get(current, []):
            tentative_g = g_score[current] + weight
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                heapq.heappush(open_set, (tentative_g, neighbor))

    exec_time = (time.perf_counter() - start_time) * 1000
    return None, float('inf'), len(explored_sequence), exec_time, explored_sequence


def greedy_best_first_search(positions, adj, start_node, goal_node):
    start_time = time.perf_counter()
    goal_pos = positions.get(goal_node, (0.0, 0.0))
    start_h = euclidean_distance(positions.get(start_node, (0.0, 0.0)), goal_pos)

    open_set = []
    heapq.heappush(open_set, (start_h, start_node))
    visited = {start_node}
    came_from = {}
    cost_so_far = {start_node: 0.0}
    explored_sequence = []

    while open_set:
        _, current = heapq.heappop(open_set)
        explored_sequence.append(current)

        if current == goal_node:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            exec_time = (time.perf_counter() - start_time) * 1000
            return path, cost_so_far[goal_node], len(explored_sequence), exec_time, explored_sequence

        for neighbor, weight in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                cost_so_far[neighbor] = cost_so_far[current] + weight
                h = euclidean_distance(positions.get(neighbor, (0.0, 0.0)), goal_pos)
                heapq.heappush(open_set, (h, neighbor))

    exec_time = (time.perf_counter() - start_time) * 1000
    return None, float('inf'), len(explored_sequence), exec_time, explored_sequence


def a_star_search(node_ids, positions, adj, start_node, goal_node):
    start_time = time.perf_counter()
    open_set = []
    heapq.heappush(open_set, (0, start_node))
    g_score = {node: float('inf') for node in node_ids}
    g_score[start_node] = 0
    goal_pos = positions.get(goal_node, (0.0, 0.0))
    came_from = {}
    explored_sequence = []

    while open_set:
        _, current = heapq.heappop(open_set)

        if current not in explored_sequence:
            explored_sequence.append(current)

        if current == goal_node:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            exec_time = (time.perf_counter() - start_time) * 1000
            return path, g_score[goal_node], len(explored_sequence), exec_time, explored_sequence

        for neighbor, weight in adj.get(current, []):
            tentative_g = g_score[current] + weight
            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = euclidean_distance(positions.get(neighbor, (0.0, 0.0)), goal_pos)
                f_score = tentative_g + h
                heapq.heappush(open_set, (f_score, neighbor))

    exec_time = (time.perf_counter() - start_time) * 1000
    return None, float('inf'), len(explored_sequence), exec_time, explored_sequence


def find_multihop_pair(sorted_nodes, adj):
    """Finds two nodes that aren't directly connected to avoid direct paths."""
    for i in range(len(sorted_nodes)):
        s = sorted_nodes[i]
        neighbors = {neighbor for neighbor, _ in adj.get(s, [])}
        for j in range(len(sorted_nodes) - 1, i, -1):
            g = sorted_nodes[j]
            if g not in neighbors and g != s:
                return s, g
    return sorted_nodes[0], sorted_nodes[-1]


def main():
    target_file = sys.argv[1] if len(sys.argv) > 1 else "graph_synthetic_20_sparse.json"
    graph_path = target_file if target_file.startswith("graphs/") else f"graphs/{target_file}"

    try:
        graph = load_graph(graph_path)
        print("\n------------------------------------------------")
        print(f" Graph Dataset: {graph_path}")
        print("------------------------------------------------")

        node_ids, positions, adj = build_normalized_graph(graph)
        print(f"Total Graph Nodes: {len(node_ids)}")

        if len(node_ids) >= 2:
            sorted_nodes = sorted(node_ids, key=lambda x: int(x) if x.isdigit() else x)

            auto_start, auto_goal = find_multihop_pair(sorted_nodes, adj)
            start_node = sys.argv[2] if len(sys.argv) > 2 else auto_start
            goal_node = sys.argv[3] if len(sys.argv) > 3 else auto_goal

            if start_node not in adj or goal_node not in adj:
                print(f"Error: Starting Node '{start_node}' or Goal Node '{goal_node}' not found in graph.")
                return

            print(f"Starting Node: '{start_node}' | Goal Node: '{goal_node}'\n")

            results = {
                "Uniform Cost Search": uniform_cost_search(node_ids, adj, start_node, goal_node),
                "Greedy Best-First Search": greedy_best_first_search(positions, adj, start_node, goal_node),
                "A* Search": a_star_search(node_ids, positions, adj, start_node, goal_node)
            }

            print(f"{'Algorithm':<24} | {'Cost':<10} | {'Explored':<10} | {'Time (ms)':<10} | {'Found?'}")
            print("-" * 72)
            for alg_name, res in results.items():
                p, c, e, t, _ = res
                print(f"{alg_name:<24} | {c:<10.2f} | {e:<10} | {t:<10.3f} | {bool(p)}")
            print("-" * 72)

            print("\n Final Paths ")
            for alg_name, res in results.items():
                p = res[0]
                if p:
                    print(f" ~ {alg_name:<24}: {' --> '.join(p)}")
                else:
                    print(f" ~ {alg_name:<24}: No Path Found")

            print("\n Order of visited nodes ")
            for alg_name, res in results.items():
                explored_seq = res[4]
                print(f" ~ {alg_name:<24}: {', '.join(explored_seq)}")

            valid_results = [r for r in results.values() if r[0] is not None]
            if valid_results:
                optimal_cost = min(r[1] for r in valid_results)
                best_alg = min(
                    [item for item in results.items() if item[1][1] == optimal_cost],
                    key=lambda x: x[1][2]
                )

                print("\n------------------------------------------------")
                print(f" The best algorithm for this dataset is {best_alg[0]}")
                print(f" Optimal Cost: {best_alg[1][1]:.2f} | Nodes Explored: {best_alg[1][2]}")
                print("------------------------------------------------")
            else:
                print("\nNo valid path found between start and goal nodes.")
        else:
            print("Warning: Graph contains fewer than 2 valid nodes to perform search.")

    except FileNotFoundError:
        print(f"Error: Could not find graph file at '{graph_path}'.")


if __name__ == "__main__":
    main()