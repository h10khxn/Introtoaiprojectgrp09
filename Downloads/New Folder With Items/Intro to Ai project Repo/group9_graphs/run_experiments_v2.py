"""Improved experiment runner (testing and evaluation).

Runs UCS, Greedy Best-First and A* from main.py (unchanged) on every ordered
start/goal pair of all 13 graphs and writes testing_package/detailed_results.csv.

What is different from run_experiments.py:
  * includes the OTU campus graph (reported separately as dataset "campus")
  * labels each case "direct" (start-goal edge exists) or "non-direct"
  * checks every path and cost against an exact Floyd-Warshall calculation
  * reports "nodes explored" under its accurate name: queue_pops
  * times each algorithm with warm-up runs, repeated batches and a
    shuffled (seeded) algorithm order
"""

import csv
import gc
import json
import math
import platform
import random
import statistics
import sys
import time
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import main

SEED = 2026
WARMUP_CASES = 20      # cases per graph run untimed before timing starts
REPEATS = 7            # timed batches per algorithm per case
CALLS_PER_REPEAT = 50  # calls per batch (one call is ~10 microseconds)

ALGORITHMS = ("UCS", "Greedy", "A*")

folder = Path(__file__).resolve().parent
out_dir = folder / "testing_package"
out_dir.mkdir(exist_ok=True)


class CountingAdjacency(dict):
    """Adjacency dict that records each adj.get(node) call.

    All three algorithms in main.py call adj.get(current, []) exactly once per
    node expansion, so this counts expansions without changing their code.
    """

    def __init__(self, data):
        super().__init__(data)
        self.expanded = []

    def get(self, key, default=None):
        self.expanded.append(key)
        return super().get(key, default)


def run(name, nodes, positions, adjacency, start, goal):
    if name == "UCS":
        return main.uniform_cost_search(nodes, adjacency, start, goal)
    if name == "Greedy":
        return main.greedy_best_first_search(nodes, positions, adjacency, start, goal)
    return main.a_star_search(nodes, positions, adjacency, start, goal)


def exact_weights(graph):
    # Weights are stored with two decimals; Fraction(str(w)) recovers them exactly.
    return {
        str(u): {str(v): Fraction(str(w)) for v, w in nbrs.items()}
        for u, nbrs in graph["adjacency"].items()
    }


def floyd_warshall(weights):
    """Exact all-pairs shortest path costs, independent of the search code."""
    nodes = list(weights)
    dist = {u: {v: (Fraction(0) if u == v else weights[u].get(v)) for v in nodes} for u in nodes}
    for k in nodes:
        for i in nodes:
            dik = dist[i][k]
            if dik is None:
                continue
            for j in nodes:
                dkj = dist[k][j]
                if dkj is not None and (dist[i][j] is None or dik + dkj < dist[i][j]):
                    dist[i][j] = dik + dkj
    return dist


def heuristic_check(positions, weights, dist):
    """Measure how far the Euclidean heuristic is from edge weights and true costs."""
    edge_over, edges_below = 0.0, 0
    for u in weights:
        for v, w in weights[u].items():
            gap = math.dist(positions[u], positions[v]) - float(w)
            if u < v and gap > 0:
                edges_below += 1
            edge_over = max(edge_over, gap)
    admissible_over = 0.0
    for goal in weights:
        for n in weights:
            if n != goal:
                over = math.dist(positions[n], positions[goal]) - float(dist[n][goal])
                admissible_over = max(admissible_over, over)
    all_cent = all((w * 100).denominator == 1 for nb in weights.values() for w in nb.values())
    return {
        "edges": sum(len(nb) for nb in weights.values()) // 2,
        "edges_weight_below_straight_line": edges_below,
        "max_consistency_overestimate": round(max(edge_over, 0.0), 6),
        "max_admissibility_overestimate": round(max(admissible_over, 0.0), 6),
        "all_weights_multiple_of_0.01": all_cent,
    }


def time_case(rng, nodes, positions, adjacency, start, goal):
    """Median/min/IQR time per call in microseconds for each algorithm."""
    samples = {name: [] for name in ALGORITHMS}
    for _ in range(REPEATS):
        order = list(ALGORITHMS)
        rng.shuffle(order)
        for name in order:
            t0 = time.perf_counter_ns()
            for _ in range(CALLS_PER_REPEAT):
                run(name, nodes, positions, adjacency, start, goal)
            samples[name].append((time.perf_counter_ns() - t0) / CALLS_PER_REPEAT / 1000)
    result = {}
    for name, values in samples.items():
        q = statistics.quantiles(values, n=4, method="inclusive")
        result[name] = (statistics.median(values), min(values), q[2] - q[0])
    return result


def main_run():
    rng = random.Random(SEED)
    rows, heuristic_rows = [], []
    files = sorted((folder / "graphs").glob("graph_*.json"))

    gc.disable()
    for file in files:
        graph = main.load_graph(file)
        nodes, positions, adjacency = main.build_normalized_graph(graph)
        nodes = sorted(nodes, key=int)
        weights = exact_weights(graph)
        dist = floyd_warshall(weights)

        campus = file.name == "graph_otu_real.json"
        dataset = "campus" if campus else "synthetic"
        layout = len(nodes)
        density = "real" if campus else file.stem.split("_")[2]
        labels = {k: v.get("label", "") for k, v in graph.get("nodes", {}).items()} if campus else {}

        heuristic_rows.append({"graph": file.name, "dataset": dataset, **heuristic_check(positions, weights, dist)})

        pairs = [(s, g) for s in nodes for g in nodes if s != g]

        # Warm-up: untimed runs so caches and the interpreter are settled.
        for s, g in pairs[:WARMUP_CASES]:
            for name in ALGORITHMS:
                for _ in range(5):
                    run(name, nodes, positions, adjacency, s, g)

        for start, goal in pairs:
            timing = time_case(rng, nodes, positions, adjacency, start, goal)
            optimal = dist[start][goal]
            case_type = "direct" if goal in weights[start] else "non-direct"

            for name in ALGORITHMS:
                counting = CountingAdjacency(adjacency)
                path, cost, pops, _ = run(name, nodes, positions, counting, start, goal)
                expanded = counting.expanded

                valid = (
                    path is not None
                    and path[0] == start
                    and path[-1] == goal
                    and len(set(path)) == len(path)
                    and all(path[i + 1] in weights[path[i]] for i in range(len(path) - 1))
                )
                exact = sum((weights[path[i]][path[i + 1]] for i in range(len(path) - 1)), Fraction(0)) if valid else None
                gap = (exact - optimal) if valid else None

                med, low, iqr = timing[name]
                rows.append({
                    "dataset": dataset,
                    "graph": file.name,
                    "layout_nodes": layout,
                    "density": density,
                    "start": start,
                    "goal": goal,
                    "start_label": labels.get(start, ""),
                    "goal_label": labels.get(goal, ""),
                    "case_type": case_type,
                    "algorithm": name,
                    "found": path is not None,
                    "path": " -> ".join(path) if path else "",
                    "path_edges": len(path) - 1 if path else "",
                    "reported_cost": round(cost, 2),
                    "exact_path_cost": float(exact) if valid else "",
                    "optimal_cost": float(optimal),
                    "path_valid": valid,
                    "reported_cost_correct": valid and abs(cost - float(exact)) < 1e-6,
                    "is_optimal": valid and exact == optimal,
                    "cost_gap": float(gap) if valid else "",
                    "cost_gap_pct": round(float(gap / optimal) * 100, 4) if valid else "",
                    "queue_pops": pops,
                    "expansions": len(expanded),
                    "distinct_nodes_expanded": len(set(expanded)),
                    "pops_not_expanded": pops - len(expanded) - (1 if path else 0),
                    "repeat_expansions": len(expanded) - len(set(expanded)),
                    "time_median_us": round(med, 3),
                    "time_min_us": round(low, 3),
                    "time_iqr_us": round(iqr, 3),
                })
        gc.collect()
        print(f"Finished: {file.name} ({len(pairs)} cases)")
    gc.enable()

    with (out_dir / "detailed_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with (out_dir / "heuristic_check.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=heuristic_rows[0].keys())
        writer.writeheader()
        writer.writerows(heuristic_rows)

    meta = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor(),
        "seed": SEED,
        "warmup_cases_per_graph": WARMUP_CASES,
        "warmup_calls_per_algorithm_per_case": 5,
        "timing_repeats": REPEATS,
        "calls_per_repeat": CALLS_PER_REPEAT,
        "algorithm_order": "shuffled per repeat with random.Random(seed)",
        "garbage_collector": "disabled during timing",
        "rows": len(rows),
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nSaved {len(rows)} rows to {out_dir / 'detailed_results.csv'}")


if __name__ == "__main__":
    main_run()
