import matplotlib.pyplot as plt


from graph_generator import load_graph
from main import (
    build_normalized_graph,
    uniform_cost_search,
    greedy_best_first_search,
    a_star_search
)

# Load the real Ontario Tech campus graph
graph = load_graph("graphs/graph_otu_real.json")

# Convert the graph into the format used by the search algorithms
node_ids, positions, adj = build_normalized_graph(graph)

# Match building names to their node IDs
building_to_node = {}

for node_id, node_data in graph["nodes"].items():
    building_to_node[node_data["label"]] = node_id

building_names = list(building_to_node.keys())


print("Graph loaded successfully!")
print("Number of nodes:", len(node_ids))

# Choose route and search algorithm
print("\nAvailable Locations:")
for name in building_names:
    print("-", name)

start_name = input("\nEnter start location: ")
goal_name = input("Enter destination: ")

print("\nAlgorithms:")
print("1 - UCS")
print("2 - Greedy Best-First")
print("3 - A*")

algorithm_choice = input("Choose algorithm (1, 2, or 3): ")

start_node = building_to_node[start_name]
goal_node = building_to_node[goal_name]

if algorithm_choice == "1":
    algorithm_name = "UCS"
    path, cost, explored, exec_time = uniform_cost_search(
        node_ids, adj, start_node, goal_node
    )

elif algorithm_choice == "2":
    algorithm_name = "Greedy Best-First"
    path, cost, explored, exec_time = greedy_best_first_search(
        node_ids, positions, adj, start_node, goal_node
    )

else:
    algorithm_name = "A*"
    path, cost, explored, exec_time = a_star_search(
        node_ids, positions, adj, start_node, goal_node
    )

print("\nRoute Results")
print("Algorithm:", algorithm_name)
print("Path:", path)
print("Cost:", round(cost, 2))
print("Nodes explored:", explored)
print("Execution time:", round(exec_time, 4), "ms")

def draw_route(graph, path, algorithm_name, cost, explored, exec_time):
    positions = graph["positions"]
    adjacency = graph["adjacency"]
    nodes = graph.get("nodes", {})

    plt.figure(figsize=(10, 8))

    # Draw every connection
    for node, neighbors in adjacency.items():
        x1, y1 = positions[node]

        for neighbor in neighbors:
            x2, y2 = positions[neighbor]

            plt.plot(
                [x1, x2],
                [y1, y2],
                color="lightgray",
                linewidth=2,
                zorder=1
            )

    # Draw the route found by the algorithm
    for i in range(len(path) - 1):
        current = path[i]
        next_node = path[i + 1]

        x1, y1 = positions[current]
        x2, y2 = positions[next_node]

        plt.plot(
            [x1, x2],
            [y1, y2],
            color="red",
            linewidth=5,
            zorder=2
        )

    # Draw all campus locations
    for node, (x, y) in positions.items():
        label = nodes.get(node, {}).get("label", node)

        plt.scatter(x, y, s=300, zorder=3)
        plt.text(
            x,
            y - 35,
            label,
            ha="center",
            fontsize=8
        )

    plt.title(
        f"{algorithm_name} Route\n"
        f"Cost: {cost:.2f} m | "
        f"Nodes Explored: {explored} | "
        f"Time: {exec_time:.4f} ms"
    )

    plt.axis("equal")
    plt.axis("off")
    plt.tight_layout()
    plt.show()


draw_route(
    graph,
    path,
    algorithm_name,
    cost,
    explored,
    exec_time
)

