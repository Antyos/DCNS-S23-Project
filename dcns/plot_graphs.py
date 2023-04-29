from functools import partial
from typing import Callable, Optional

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.animation import FuncAnimation

from dcns.graph_utils import Graph, Node, PosDict
from dcns.pathfinding import SearchGenerator, pathfind_steps


def plot_graph(
    graph: Graph,
    pos: PosDict,
    ax: plt.Axes,
    min_edge_length=0.007,
    style: Optional[dict] = None,
    edges=None,
):
    """Plot a graph but without edges below a threshold.

    Parameters
    ----------
    graph: nx.Graph | nx.DiGraph
    pos: dic of positions
    ax: plt.Axes
    min_edge_length: float
        Edges below this length will not be plotted. Increase to plot faster, but display
        fewer edges
    style: dict (optional)
        Style for graph
    edges: iterable of edges (optional)
        If trying to plot a subgraph, there is a bug where the edges will not display.
        If that is the case, pass in the edges from the original graph here.
    """
    if style is None:
        style = {}
    # Only draw edges over a threshold for faster displaying. It is very dumb that we
    # need to check the endpoints of the edges being in the component's nodes, but for
    # some reason, doing G.edges() on the subgraph yields no edges, so this is the only
    # way.
    edges = [
        (u, v)
        for u, v in edges or graph.edges()
        if np.linalg.norm(pos[u] - pos[v]) > min_edge_length
        and u in graph.nodes
        and v in graph.nodes
    ]
    nx.draw_networkx_edges(
        graph,
        pos=pos,
        ax=ax,
        edgelist=edges,
        alpha=0.4,
        width=0.5,
        **style,
    )
    nx.draw_networkx_nodes(graph, pos=pos, ax=ax, node_color="tab:blue", **style)
    ax.set_aspect("equal")


def plot_pathfinding(
    graph: Graph,
    search_func: Callable[[Graph, Node, Node], SearchGenerator],
    start: Node,
    end: Node,
    min_edge_length=0.007,
    sample_steps: tuple[int, int] = (200, 10),
    title: str = "",
    style: Optional[dict] = None,
):
    """Animates the pathfinding steps

    Parameters
    ----------
    graph: nx.Graph | nx.DiGraph
    search_func: func(Graph, Node, Node) -> SearchGenerator
        Used to generate the pathfinding steps
    start: Node
        Starting node
    end: Node
        Ending node
    min_edge_length: float (default, 0.007)
        Edges below this length will not be plotted. Increase to plot faster, but display
        fewer edges
    sample_steps: tuple of (int, int)
        How many iterations of the search or back-tracing phases do we do before adding
        a frame to the animation.
    style: dict
        Style of graph

    Returns:
    --------
    matplotlib.animation.FuncAnimation
    """
    pos = nx.get_node_attributes(graph, "pos")

    if style is None:
        style = {}

    steps = pathfind_steps(
        search_generator=search_func(graph, start, end),
        start=start,
        end=end,
        sample_steps=sample_steps,
    )
    steps.insert(0, steps[0])  # Artificially extend the length of the first frame

    fig, ax = plt.subplots(figsize=(6, 6))

    def update(frame: int):
        if frame >= len(steps):
            return

        searched_nodes, path_nodes = steps[frame]

        # Draw the updated graph with new node colors
        nx.draw_networkx_nodes(
            graph,
            pos=pos,
            ax=ax,
            nodelist=searched_nodes,
            node_color="tab:orange",
            # Pylance doesn't know that style==None has already been taken care of
            **style,  # type: ignore
        )
        nx.draw_networkx_nodes(
            graph,
            pos=pos,
            ax=ax,
            nodelist=path_nodes,
            node_color="tab:green",
            # Pylance doesn't know that style==None has already been taken care of
            **style,  # type: ignore
        )

    if title:
        # fig.suptitle(title)
        ax.set_title(title)
    fig.tight_layout()
    fig.subplots_adjust(left=0, right=1, wspace=0)

    # Create an animation object
    return FuncAnimation(
        fig,
        update,
        init_func=partial(
            plot_graph, graph, pos, ax, min_edge_length=min_edge_length, style=style
        ),
        interval=100,
        frames=len(steps) + 3,
        repeat=True,
    )
