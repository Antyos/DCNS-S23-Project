import itertools

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm


def convolve_iter(arr: NDArray):
    """Iterate though an NDArray, yielding a flattened NDArray of the 3x3 surrounding cells."""
    for i, j in itertools.product(range(arr.shape[0]), range(arr.shape[1])):
        # get the indices of the cell's neighbors
        i1 = max(i - 1, 0)
        i2 = min(i + 2, arr.shape[0])
        j1 = max(j - 1, 0)
        j2 = min(j + 2, arr.shape[1])

        # sum the values of the cell and its neighbors
        yield arr[i1:i2, j1:j2].flatten()


def get_partition_size(node_positions: dict[str, NDArray], num_partitions: int):
    """Get the (x,y) size of each partition"""
    # determine the min and max x and y values
    x_min, y_min = np.min(list(node_positions.values()), axis=0)
    x_max, y_max = np.max(list(node_positions.values()), axis=0)

    # calculate the partition size in x and y directions
    return ((x_max - x_min) / num_partitions, (y_max - y_min) / num_partitions)


def partition_nodes(node_positions: dict[str, NDArray], num_partitions: int):
    """Partition a dictionary of positions into a grid"""
    # determine the min and max x and y values
    x_min, y_min = np.min(list(node_positions.values()), axis=0)
    x_max, y_max = np.max(list(node_positions.values()), axis=0)

    # calculate the partition size in x and y directions
    x_partition_size, y_partition_size = get_partition_size(
        node_positions, num_partitions
    )

    # create the partitions array
    partitions = np.empty((num_partitions, num_partitions), dtype=object)
    partitions[:] = [
        [set() for _ in range(partitions.shape[1])] for _ in range(partitions.shape[0])
    ]
    # partitions[:] = [[]*num_partitions]*num_partitions

    # assign each node to its corresponding partition
    for node_name, node_pos in node_positions.items():
        x_index = int((node_pos[0] - x_min) // x_partition_size) - 1
        y_index = int((node_pos[1] - y_min) // y_partition_size) - 1
        partitions[x_index, y_index].add(node_name)

    return partitions


def get_close_edges(
    pos: dict[str, NDArray], max_distance=0.001, num_partitions=50, show_progress=True
):
    partitions = partition_nodes(pos, num_partitions)
    close_edges: set[tuple[str, str]] = set()

    # Make sure our distance threshold is smaller than the size of the partitions
    x_partition_size, y_partition_size = get_partition_size(pos, num_partitions)
    if max_distance >= x_partition_size or max_distance >= y_partition_size:
        raise ValueError(
            f"Partition size {x_partition_size, y_partition_size} for {num_partitions} "
            f"partitions is smaller than max_distance {max_distance}"
        )

    for cell in tqdm(
        convolve_iter(partitions), total=num_partitions**2, disable=not show_progress
    ):
        nodes = set.union(*cell)
        # total_combinations = len(nodes) * (len(nodes)-1)

        close_edges.update(
            (u, v)
            for u, v in itertools.combinations(nodes, 2)
            # ), total=total_combinations, desc="Nodes in cell")
            if np.linalg.norm(pos[u] - pos[v]) < max_distance
        )
    return close_edges
