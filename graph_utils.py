from typing import Iterable, TypeVar, Union

import networkx as nx
import numpy as np

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


def node_list_to_ndarray(G: Graph, attr: str):
    """Convert node attributes of a graph from a list to a numpy array"""
    nx.set_node_attributes(
        G,
        {node: np.array(pos) for node, pos in nx.get_node_attributes(G, attr).items()},
        attr,
    )


def node_ndarray_to_list(G: Graph, attr: str):
    """Convert node attributes of a graph from a numpy array to a list"""
    nx.set_node_attributes(
        G,
        {node: pos.tolist() for node, pos in nx.get_node_attributes(G, attr).items()},
        attr,
    )
