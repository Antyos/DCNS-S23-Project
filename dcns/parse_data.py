# %%
import itertools
from datetime import timedelta
from pathlib import Path

import more_itertools
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from tqdm import tqdm

try:
    from .close_edges import with_close_edges
    from .graph_utils import node_attr_ndarray_to_list, remove_edge_attrs
    from .plot_graphs import plot_graph
except ImportError:
    from close_edges import with_close_edges  # type: ignore
    from graph_utils import node_attr_ndarray_to_list, remove_edge_attrs  # type: ignore
    from plot_graphs import plot_graph  # type: ignore

DATA_DIR = Path(__file__).parent / "../data/"
DART_DATA_DIR = DATA_DIR / "gtfs-dart-2023-02-28"

# %%
routes = pd.read_csv(DART_DATA_DIR / "routes.txt")
trips = pd.read_csv(DART_DATA_DIR / "trips.txt")
stop_times = pd.read_csv(DART_DATA_DIR / "stop_times.txt")
stops = pd.read_csv(DART_DATA_DIR / "stops.txt")


# Convert stop times to actual times
def time_string_to_timedelta(time_string):
    hours, minutes, seconds = [int(x) for x in time_string.split(":")]
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


stop_times["arrival_time_sec"] = stop_times.arrival_time.apply(
    time_string_to_timedelta
).dt.total_seconds()
stop_times["departure_time_sec"] = stop_times.departure_time.apply(
    time_string_to_timedelta
).dt.total_seconds()


def graph_common_data_fields(data_dir: Path, draw=True):
    """Graph the common columns from data files."""
    # Read all files in DATA_DIR
    d = {f.stem: pd.read_csv(f) for f in data_dir.iterdir()}

    cols = pd.DataFrame(
        data={name: pd.Series(d[name].columns.str.casefold()) for name in d}
    )

    # % Display a graph based on fields that link each file
    G = nx.Graph()
    G.add_nodes_from(cols.keys())
    for u, v in itertools.permutations(cols.keys(), 2):
        common_fields = set(cols[u].dropna()) & set(cols[v].dropna())
        if common_fields:
            # print(common_fields)
            G.add_edge(u, v, weight=len(common_fields), fields=",".join(common_fields))

    G.remove_nodes_from(list(nx.isolates(G)))

    if draw:
        pos = nx.spring_layout(G, 1)
        nx.draw(G, pos, with_labels=True)
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=nx.get_edge_attributes(G, "fields")
        )

    return G


def make_graph():
    # Flow of data lookups to generate routes
    # routes --route_id-> trips --trip_id-> stop_times --stop_id-> stops

    G = nx.DiGraph()

    r1 = routes.route_id[0]
    r1_trips = trips[trips.route_id == r1]
    # for trip_id in list(r1_trips["trip_id"].drop_duplicates())[140:150]:
    for trip_id in tqdm(trips["trip_id"].drop_duplicates()):
        trip_stop_times = (
            stop_times[stop_times.trip_id == trip_id]
            .set_index("stop_sequence")
            .sort_index()
        )
        for s1, s2 in more_itertools.pairwise(trip_stop_times.itertuples(index=False)):
            trip_time = s2.arrival_time_sec - s1.arrival_time_sec
            if not G.has_edge(s1.stop_id, s2.stop_id):
                G.add_edge(s1.stop_id, s2.stop_id, trip_times=[trip_time])
            else:
                G[s1.stop_id][s2.stop_id]["trip_times"].append(trip_time)
        # trip_stop_names = trip_stop_ids.map(stops.set_index("stop_id")["stop_name"])

    nx.set_node_attributes(G, get_stop_pos(stops), "pos")
    nx.set_node_attributes(G, stops.set_index("stop_id").stop_name.to_dict(), "name")
    add_edge_attributes(G)

    return G


def get_stop_pos(stops) -> dict:
    """Get stop locations based on latitude / longitude as a dictionary

    Uses the networkx format:
        { node_id: np.array([x, y]), ... }
    In the case of the stops data, this looks like:
        { stop_id: np.array([stop_lon, stop_lat]), ... }
    """
    return (
        stops.set_index("stop_id")[["stop_lon", "stop_lat"]]
        .apply(lambda row: np.array(row.values), axis=1)
        .to_dict()
    )


def add_edge_attributes(G):
    """Add number of trips & avg time time to edges"""
    num_trips = {
        trip: len(times)
        for trip, times in nx.get_edge_attributes(G, "trip_times").items()
    }
    nx.set_edge_attributes(G, num_trips, "num_trips")

    avg_trip_time = {
        trip: round(sum(times) / len(times), 2)
        for trip, times in nx.get_edge_attributes(G, "trip_times").items()
    }
    nx.set_edge_attributes(G, avg_trip_time, "avg_trip_time")


def save_gml(G, output_path):
    # Edges may have a few hundred trips each which would clutter the .gml file so we purge
    # them first
    Gout = remove_edge_attrs(G.__class__(G), "trip_times")
    # Convert pos from numpy array to list so it can be exported as gml
    node_attr_ndarray_to_list(Gout, "pos")
    nx.write_gml(Gout, output_path)


# %%

# Full Graph
G = make_graph()

# Largest component
G2 = G.__class__(G.subgraph(max(nx.strongly_connected_components(G), key=len)))

# With close edges
close_edge_threshold = 0.00085
G3 = with_close_edges(G2, close_edge_threshold, avg_trip_time=20, num_trips=100_000)

save_gml(G, DATA_DIR / "dartstops_full.gml")
save_gml(G2, DATA_DIR / "dartstops_largest_component.gml")
save_gml(G2, DATA_DIR / "dartstops_largest_component_with_close_edges.gml")

# %% Plot
stop_pos = get_stop_pos(stops)
fig, ax = plt.subplots()
plot_graph(G, stop_pos, ax)
