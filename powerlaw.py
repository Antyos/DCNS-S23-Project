import itertools
from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def degree_sequence(G: nx.Graph):
    deg = G.degree()
    return [deg] if isinstance(deg, int) else [d for _, d in deg]


def degree_distribution(G: nx.Graph, normalize=True):
    deg_sequence = degree_sequence(G)
    max_degree = np.max(deg_sequence)
    ddist = np.zeros((max_degree + 1,))
    for d in deg_sequence:
        ddist[d] += 1
    if normalize:
        ddist /= float(G.number_of_nodes())
    return ddist


def cumulative_degree_distribution(G: nx.Graph):
    ddist = degree_distribution(G)
    return np.array([ddist[k:].sum() for k in range(len(ddist))])


def calc_powerlaw_ax(
    axes: tuple[plt.Axes, plt.Axes], G: nx.Graph, kmin: Optional[int] = None
):
    """Plot powerlaw PDF/CDF for a pair of axes."""
    deg_seq = np.array(degree_sequence(G))
    deg_dist = degree_distribution(G, normalize=False)
    cum_dist = cumulative_degree_distribution(G)

    if kmin is not None:
        # Number of nodes above cutoff degree
        N = np.count_nonzero(deg_seq >= (kmin or 0))
        # Make sure we have some nodes so we don't divide by 0
        assert N > 0

        # Newman Eq (8.6): α = 1+N/Σ[ln({k_i}/{k_min}-0.5})]
        alpha = 1 + N / sum(np.log(ki / (kmin - 0.5)) for ki in deg_seq if ki >= kmin)
        # Newman Eq (8.7): σ = (α-1)/√N
        sigma = (alpha - 1) / np.sqrt(N)
    else:
        alpha = None
        sigma = None

    # PDF
    axes[0].bar(*zip(*enumerate(deg_dist)), width=0.8, bottom=0, color="b")

    # CDF
    axes[1].loglog(*zip(*enumerate(cum_dist)))
    if kmin is not None:
        axes[1].axvline(kmin, color="orange", linestyle="dashed")
    axes[1].grid(True)

    if alpha is not None and sigma is not None:
        return (alpha, sigma)


def calc_powerlaw_multi(
    graphs: dict[str, nx.Graph],
    kmins: Optional[list[int]] = None,
    *,
    title: str = "",
    sharey: bool = False,
    figsize: tuple[float, float] = (12, 8),
):
    """Plot degree distribution PDF/CDF for several graphs"""
    fig, axes = plt.subplots(
        nrows=2,
        ncols=len(graphs),
        figsize=figsize,
        sharey=sharey,
    )

    axes_by_col = np.atleast_2d(axes).T

    # Default to empty lists for zip
    kmins = kmins or []

    # For each graph
    for (name, G), kmin, ax in itertools.zip_longest(
        graphs.items(), kmins, axes_by_col
    ):
        exponent = calc_powerlaw_ax(ax, G, kmin)

        exponent_str = (
            f"α±σ = {exponent[0]:1.2f} +/- {exponent[1]:1.2f}"
            if exponent is not None
            else None
        )

        # Form the column title from the user-specified caption and exponent string,
        # separated by a new line if both exist
        col_title = "\n".join([s for s in (name, exponent_str) if s is not None])

        if col_title:
            ax[0].set_title(col_title)

    # Set y labels for PDF (top row) and CDF (bottom row)
    axes_by_col[0][0].set_ylabel("PDF")
    axes_by_col[0][1].set_ylabel("CDF")

    # Set top-level figure stuff
    if title:
        fig.suptitle(title)

    return fig
