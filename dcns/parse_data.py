# %%
import itertools
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

import more_itertools
import networkx as nx
import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    from .graph_utils import node_attr_ndarray_to_list, remove_edge_attrs
except ImportError:
    from graph_utils import node_attr_ndarray_to_list, remove_edge_attrs  # type: ignore

DATA_DIR = Path(__file__).parent / "../data/gtfs-dart-2023-02-28"

# %%
routes = pd.read_csv(DATA_DIR / "routes.txt")
trips = pd.read_csv(DATA_DIR / "trips.txt")
stop_times = pd.read_csv(DATA_DIR / "stop_times.txt")
stops = pd.read_csv(DATA_DIR / "stops.txt")


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


def make_graph(flag):
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
    add_edge_attributes(G,flag)

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


def add_edge_attributes(G,flag):
    """Add number of trips & avg time time to edges"""
    num_trips = {
        trip: len(times)
        for trip, times in nx.get_edge_attributes(G, "trip_times").items()
    }
    avg_trip_times = {
        trip: round(sum(times) / len(times), 2)
        for trip, times in nx.get_edge_attributes(G, "trip_times").items()
    }
    num_trips_over5000 = {
        trip: num_trips[trip]/5000
        for trip, times in nx.get_edge_attributes(G, "trip_times").items()
    }
    if flag == 1:
        nx.set_edge_attributes(G, num_trips, "num_trips")
        nx.set_edge_attributes(G, avg_trip_times, "weight")
    elif flag == 2:
        nx.set_edge_attributes(G, num_trips, "weight")
        nx.set_edge_attributes(G, avg_trip_times, "avg_trip_times")
    elif flag == 3:
        nx.set_edge_attributes(G, num_trips_over5000, "weight")
        nx.set_edge_attributes(G, avg_trip_times, "avg_trip_times")
    else:
        print("Put either 1 2 or 3 in the second argument")


def save_gml(G, output_path):
    # Edges may have a few hundred trips each which would clutter the .gml file so we purge
    # them first
    Gout = remove_edge_attrs(G.__class__(G), "trip_times")
    # Convert pos from numpy array to list so it can be exported as gml
    node_attr_ndarray_to_list(Gout, "pos")
    nx.write_gml(Gout, output_path)


# %%

G_time = make_graph(1)
G_freq = make_graph(2)
G_freq_over5000 = make_graph(3)
stop_pos = get_stop_pos(stops)
nx.draw(G_time, stop_pos, node_size=5, width=0.5)

save_gml(G_time, "../data/dart_stops_time.gml")
save_gml(G_freq, "../data/dart_stops_freq.gml")
save_gml(G_freq_over5000, "../data/dart_stops_freq_over5000.gml")
