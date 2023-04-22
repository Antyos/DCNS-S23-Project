import itertools
from typing import Iterable

import networkx as nx
import numpy as np


def modularity(G: nx.DiGraph, c: Iterable[set[str]]):
    d = {n: k for k, v in enumerate(c) for n in v}

    L = sum(data["weight"] for _, _, data in G.edges.data())

    Q, Qmax = 0, 1
    for u, v in itertools.product(G.nodes(), repeat=2):
        if d[u] == d[v]:
            Auv = G[v][u].get("weight", 0) if G.has_edge(v, u) else 0
            Q += (
                Auv
                - G.in_degree(u, weight="weight") * G.out_degree(v, weight="weight") / L
            ) / L
            Qmax -= (
                G.in_degree(u, weight="weight") * G.out_degree(v, weight="weight") / L
            ) / L
    return Q, Qmax


def scalar_assortativity(G, d: dict):
    x = np.zeros(G.number_of_nodes())
    for i, n in enumerate(G.nodes()):
        x[i] = d[n]

    A = nx.to_numpy_array(G).T
    M = 2 * A.sum().sum()
    ki = A.sum(axis=1)  # row sum is in-degree
    ko = A.sum(axis=0)  # column sum is out-degree
    mu = (np.dot(ki, x) + np.dot(ko, x)) / M

    R, Rmax = 0, 0
    for i, j in itertools.product(range(G.number_of_nodes()), repeat=2):
        R += (A[i, j] * (x[i] - mu) * (x[j] - mu)) / M
        Rmax += (A[i, j] * (x[i] - mu) ** 2) / M

    return R, Rmax
