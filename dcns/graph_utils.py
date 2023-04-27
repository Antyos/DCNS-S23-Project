import itertools
from typing import Any, Iterable, TypeVar, Union

import networkx as nx
import numpy as np
from numpy.typing import NDArray

Node = Any
Graph = Union[nx.Graph, nx.DiGraph]

GGraph = TypeVar("GGraph", bound=Graph)
"""Generic version of `Union[nx.Graph, nx.DiGraph]` for return types"""


def remove_edge_attrs(G: GGraph, attrs: Union[Iterable[str], str]) -> GGraph:
    """Remove edge attributes from a graph"""
    for n1, n2, d in G.edges(data=True):
        if isinstance(attrs, str):
            d.pop(attrs)
        for attr in attrs:
            d.pop(attr, None)
    return G


def node_attr_list_to_ndarray(G: Graph, attr: str):
    """Convert node attributes of a graph from a list to a numpy array"""
    nx.set_node_attributes(
        G,
        {node: np.array(pos) for node, pos in nx.get_node_attributes(G, attr).items()},
        attr,
    )


def node_attr_ndarray_to_list(G: Graph, attr: str):
    """Convert node attributes of a graph from a numpy array to a list"""
    nx.set_node_attributes(
        G,
        {node: pos.tolist() for node, pos in nx.get_node_attributes(G, attr).items()},
        attr,
    )


def bibliographic_coupling(G: nx.DiGraph) -> nx.Graph:
    B = nx.Graph()
    B.add_nodes_from(G.nodes())

    for ni, nj in itertools.permutations(G.nodes, 2):
        weight = sum(
            G[ni][nk]["weight"] * G[nj][nk]["weight"]
            for nk in (set(G.successors(ni)) & set(G.successors(nj)))
        )

        if weight != 0:
            B.add_edge(nj, ni, weight=weight)

    return B


def cocitation(G: nx.DiGraph) -> nx.Graph:
    C = nx.Graph()
    C.add_nodes_from(G.nodes())

    for ni, nj in itertools.permutations(G.nodes, 2):
        weight = sum(
            G[nk][ni]["weight"] * G[nk][nj]["weight"]
            for nk in (set(G.predecessors(ni)) & set(G.predecessors(nj)))
        )

        if weight != 0:
            C.add_edge(nj, ni, weight=weight)

    return C


BBox = Union[
    list[list[float]],
    tuple[tuple[float, float], tuple[float, float]],
    NDArray[np.floating],
]


def in_bbox(point, bbox: BBox) -> bool:
    """True if a point is inside a bounding box."""
    return bbox[0][0] <= point[0] <= bbox[0][1] and bbox[1][0] <= point[1] <= bbox[1][1]


def crop_graph(G: Graph, node_pos: dict, bbox: BBox):
    """Get a subgraph based on node positions inside a bounding box"""
    nodes_inside = [node for node in G.nodes() if in_bbox(node_pos[node], bbox)]
    return G.__class__(G.subgraph(nodes_inside))
