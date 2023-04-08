# %%
import itertools
from pathlib import Path

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
    trip_stop_ids = stop_times[stop_times.trip_id == trip_id].stop_id
    G.add_edges_from(more_itertools.pairwise(trip_stop_ids.values))
    # trip_stop_names = trip_stop_ids.map(stops.set_index("stop_id")["stop_name"])

# %% Convert the trip into a DiGraph
nx.draw(G, stop_pos, node_size=5, width=0.5)
# G.add_nodes_from(trip1_stop_times.stop_id.values)


# %%
