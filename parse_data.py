# %%
import itertools
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Union

import more_itertools
import networkx as nx
import numpy as np
import pandas as pd

DATA_DIR = Path("data/gtfs-dart-2023-02-28")

# %%
nodes = pd.read_csv(DATA_DIR / "nodes.txt")
routes = pd.read_csv(DATA_DIR / "routes.txt")
trips = pd.read_csv(DATA_DIR / "trips.txt")
stop_times = pd.read_csv(DATA_DIR / "stop_times.txt")
stops = pd.read_csv(DATA_DIR / "stops.txt")

# Read all files in DATA_DIR
d = {f.stem: pd.read_csv(f) for f in DATA_DIR.iterdir()}


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

# %% Get the columns from each file for comparison
cols = pd.DataFrame(data={name: pd.Series(d[name].columns.str.lower()) for name in d})

# %% Display a graph based on fields that link each file
G = nx.Graph()
G.add_nodes_from(cols.keys())
for u, v in itertools.permutations(cols.keys(), 2):
    common_fields = set(cols[u].dropna()) & set(cols[v].dropna())
    if common_fields:
        # print(common_fields)
        G.add_edge(u, v, weight=len(common_fields), fields=",".join(common_fields))

G.remove_nodes_from(list(nx.isolates(G)))

# Draw
pos = nx.spring_layout(G, 1)
nx.draw(G, pos, with_labels=True)
nx.draw_networkx_edge_labels(G, pos, edge_labels=nx.get_edge_attributes(G, "fields"))


# %%
def latlon_to_pos(row):
    return np.array(row.values)


# Get stop locations based on latitude / longitude as a dictionary networkx format:
# { node_id: np.array([x, y]), ... }
# In the case of the stops data, this looks like:
# { stop_id: np.array([stop_lon, stop_lat]), ... }
stop_pos = (
    stops.set_index("stop_id")[["stop_lon", "stop_lat"]]
    .apply(latlon_to_pos, axis=1)
    .to_dict()
)

# %%

# Flow of data lookups to generate routes
# routes --route_id-> trips --trip_id-> stop_times --stop_id-> stops

# r1_name = routes.route_short_name[0]

# The short names from nodes.txt are misleading because nodes.txt is a pain.
# There are duplicate entries for stops and not all stops are included there.
# short_names = (
#     nodes[nodes.ROUTE_NAME_SHORT == r1_name][["NODE", "STOP_ID"]]
#     .drop_duplicates()
#     .set_index("STOP_ID")
#     .drop_duplicates()
# )
G = nx.DiGraph()

r1 = routes.route_id[0]
r1_trips = trips[trips.route_id == r1]
# for trip_id in r1_trips["trip_id"].drop_duplicates():
for trip_id in trips["trip_id"].drop_duplicates():
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

# %% Average trip times for each node
num_trips = {
    trip: len(times) for trip, times in nx.get_edge_attributes(G, "trip_times").items()
}
avg_trip_times = {
    trip: round(sum(times) / len(times), 2)
    for trip, times in nx.get_edge_attributes(G, "trip_times").items()
}

nx.set_edge_attributes(G, num_trips, "num_trips")
nx.set_edge_attributes(G, avg_trip_times, "weight")


# %% Remove list of trip times
def remove_edge_attrs(G, attrs: Union[Iterable[str], str]):
    for n1, n2, d in G.edges(data=True):
        if isinstance(attrs, str):
            d.pop(attrs)
        for attr in attrs:
            d.pop(attr, None)
    return G


# %% Convert the trip into a DiGraph
nx.draw(G, stop_pos, node_size=5, width=0.5)
# G.add_nodes_from(trip1_stop_times.stop_id.values)


# %% Write the graph to .gml
Gout = G.__class__(G)
Gout = remove_edge_attrs(Gout, "trip_times")
nx.write_gml(Gout, "data/dart_stops.gml.gz")
# %%