import heapq
from collections import deque
from typing import Any, Generator, Optional

import networkx as nx

from .graph_utils import Graph

Node = Any

SearchGenerator = Generator[tuple[dict[Node, None], dict[Node, float]], None, None]
"""Pathfinding search generator.

Yields:
predecessor: dict
distance: dict
"""


class NoPathBetweenNodes(ValueError):
    def __init__(self, node1: str, node2: str):
        self.node1 = node1
        self.node2 = node2
        message = f'No path exists between nodes "{node1}" and "{node2}"'
        super().__init__(message)


### SEARCH GENERATOR FUNCTIONS ###


def astar_search(
    graph: Graph,
    start: Node,
    end: Node,
    heuristic: Optional[dict[Node, float]] = None,
) -> SearchGenerator:
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


def bfs_search(graph: Graph, start: Node, end: Node) -> SearchGenerator:
    """
    Find the shortest path between two nodes in a weighted graph using BFS algorithm.

    Args:
        graph: The input graph represented as a NetworkX Graph object.
        start: The index of the start node.
        end: The index of the end node.

    Returns:
        A tuple containing the shortest path as a list of node IDs and its total length.
    """
    # Initialize the distances of all nodes to infinity
    distance = {node: float("inf") for node in graph.nodes()}
    distance[start] = 0

    # Initialize the predecessor dictionary
    predecessor = {start: None}

    # Initialize the queue with the start node
    queue = [start]

    while queue:
        # Pop the node from the front of the queue
        curr_node = queue.pop(0)

        # If we've reached the end node, terminate early
        if curr_node == end:
            return

        # Iterate over the neighbors of the current node
        neighbors = (
            graph.successors(curr_node)
            if isinstance(graph, nx.DiGraph)
            else graph.neighbors(curr_node)
        )
        for neighbor in neighbors:
            # Calculate the distance from the current node to the neighbor
            edge_weight = graph[curr_node][neighbor]["weight"]
            neighbor_dist = distance[curr_node] + edge_weight

            # Update the distance and predecessor of the neighbor if a shorter path was found
            if neighbor not in distance or neighbor_dist < distance[neighbor]:
                distance[neighbor] = neighbor_dist
                predecessor[neighbor] = curr_node

                # Add the neighbor to the queue
                queue.append(neighbor)
            yield predecessor, distance

    # If the end node was not found, raise an exception
    raise NoPathBetweenNodes(start, end)


### GENERIC PATHFINDING FUNCTIONS ###


def predecessor_path(predecessor: dict, start: Node, end: Node):
    # Construct the shortest path from the predecessor dictionary
    path = [end]
    while path[-1] != start:
        path.append(predecessor[path[-1]])
        yield path

    return path


def pathfind(search_generator: SearchGenerator, start: Node, end: Node):
    """Generic pathfind using a search generator function and start/end nodes."""
    try:
        # Use deque to get the last item in the generator
        predecessor, distance = deque(search_generator, maxlen=1).pop()
    except NoPathBetweenNodes:
        raise
    path = deque(predecessor_path(predecessor, start, end), maxlen=1).pop()
    path.reverse()

    return path, distance[end], len(predecessor)


def pathfind_steps(
    search_generator: SearchGenerator, start: Node, end: Node, sample_steps=(100, 5)
):
    """Get a tuple of (searched_nodes, path_nodes) for each pathfinding solve step.

    Parameters
    ----------
    sample_steps: Take every n samples of the predecessors or search steps
    """
    # Search phase
    try:
        # We have to make a copy of each dictionary because it is mutated at each step.
        predecessors = [dict(predecessor) for predecessor, _ in search_generator]
    except NoPathBetweenNodes:
        raise

    steps: list[tuple[tuple[Node, ...], tuple[Node, ...]]] = [
        (tuple(predecessor.keys()), ())
        for predecessor in predecessors[:: sample_steps[0]]
    ]

    final_predecessors = tuple(predecessors[-1].keys())

    # Path phase
    paths = [tuple(path) for path in predecessor_path(predecessors[-1], start, end)]

    steps.extend(
        (final_predecessors, tuple(path)) for path in paths[:: sample_steps[1]]
    )

    # Make sure to include the last step in there
    if len(paths) - 1 % sample_steps[1] != 0:
        steps.append((final_predecessors, paths[-1]))

    return steps


### ACTUAL PATHFINDING FUNCTIONS ###


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
    try:
        return pathfind(astar_search(graph, start, end, heuristic), start, end)
    except NoPathBetweenNodes:
        raise


def dijkstra(graph: Graph, start: Node, end: Node):
    """Get the shortest path between two nodes in a graph using Dijkstra's algorithm.

    Returns
    -------
    final_path: list of Nodes
    distance: length of path (sum of edgeweights)
    num_nodes_searched: number of nodes searched before finding the path
    """
    heuristic = {node: 0.0 for node in graph.nodes()}
    try:
        return pathfind(astar_search(graph, start, end, heuristic), start, end)
    except NoPathBetweenNodes:
        raise


def bfs(graph: Graph, start: Node, end: Node):
    """Get the shortest path between two nodes in a graph using Breadth-First Search.

    Returns
    -------
    final_path: list of Nodes
    distance: length of path (sum of edgeweights)
    num_nodes_searched: number of nodes searched before finding the path
    """
    try:
        return pathfind(bfs_search(graph, start, end), start, end)
    except NoPathBetweenNodes:
        raise
