import heapq
from collections import deque
from typing import Any, Optional

import networkx as nx

from .graph_utils import Graph

Node = Any


class NoPathBetweenNodes(ValueError):
    def __init__(self, node1: str, node2: str):
        self.node1 = node1
        self.node2 = node2
        message = f'No path exists between nodes "{node1}" and "{node2}"'
        super().__init__(message)


def astar_search(
    graph: Graph,
    start: Node,
    end: Node,
    heuristic: Optional[dict[Node, float]] = None,
):
    """Find the shortest path between two nodes in a weighted graph using the a* algorithm."""
    # Determine if the graph is directed or undirected
    is_directed = isinstance(graph, nx.DiGraph)

    # Set the heuristic to zero if not provided
    if not heuristic:
        heuristic = {node: 0.0 for node in graph.nodes()}

    # Initialize the distances of all nodes to infinity
    distance: dict[Node, float] = {node: float("inf") for node in graph.nodes()}
    distance[start] = 0

    # Initialize the heap queue with the start node
    heap = [(0 + heuristic[start], start)]

    # Initialize the predecessor dictionary
    predecessor = {}

    while heap:
        # Pop the node with the minimum distance from the heap queue
        _, curr_node = heapq.heappop(heap)

        # If we've reached the end node, terminate early
        if curr_node == end:
            return

        # Iterate over the neighbors of the current node
        neighbors = (
            graph.successors(curr_node) if is_directed else graph.neighbors(curr_node)  # type: ignore
        )
        for neighbor in neighbors:
            # Calculate the distance from the current node to the neighbor
            edge_weight = graph[curr_node][neighbor]["weight"]
            new_dist = distance[curr_node] + edge_weight

            # Update the distance and predecessor of the neighbor if a shorter path was found
            if new_dist < distance[neighbor]:
                distance[neighbor] = new_dist
                predecessor[neighbor] = curr_node

                # Add the neighbor to the heap queue
                heapq.heappush(heap, (new_dist + heuristic[curr_node], neighbor))

        yield predecessor, distance

    raise NoPathBetweenNodes(start, end)


def predecessor_path(predecessor: dict, start: Node, end: Node):
    # Construct the shortest path from the predecessor dictionary
    path = [end]
    while path[-1] != start:
        path.append(predecessor[path[-1]])
        yield path

    return path


def astar(
    graph: Graph,
    start: Node,
    end: Node,
    heuristic: Optional[dict[Node, float]] = None,
):
    """Get the shortest path between two nodes in a graph using the a* algorithm.

    Returns
    -------
    final_path: list of Nodes
    distance: length of path (sum of edgeweights)
    num_nodes_searched: number of nodes searched before finding the path
    """
    # Use deque to get the last item in the generator
    try:
        predecessor, distance = deque(
            astar_search(graph, start, end, heuristic), maxlen=1
        ).pop()
    except NoPathBetweenNodes:
        raise
    path = deque(predecessor_path(predecessor, start, end), maxlen=1).pop()
    path.reverse()

    return path, distance[end], len(predecessor)


def dijkstra(
    graph: Graph,
    start: Node,
    end: Node,
):
    """Get the shortest path between two nodes in a graph using Dijkstra's algorithm.

    Returns
    -------
    final_path: list of Nodes
    distance: length of path (sum of edgeweights)
    num_nodes_searched: number of nodes searched before finding the path
    """
    heuristic = {node: 0.0 for node in graph.nodes()}
    # Use deque to get the last item in the generator
    return astar(graph, start, end, heuristic)
