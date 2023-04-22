# DCNS S23 - Project

Andrew Glick, David Simpson

## Description

Final project for UTD SYSM 6302 / MECH 6317 S23. Analysis of DART bus network.

> Data obtained from: www.dart.org/transitdata/latest/google_transit.zip
> See also: DART GTFS data on [MobilityData/mobility-database-catalogs](https://github.com/MobilityData/mobility-database-catalogs/blob/c74327f4a4955ee0189f261478fb04807c067334/catalogs/sources/gtfs/schedule/us-texas-dallas-area-rapid-transit-dart-gtfs-152.json#L4)

## Analysis

- [ ] Alignment
- [ ] Assortativty (N/A)
- [ ] Centrality <-- [DS]
- [ ] Clustering <-- [DS]
- [ ] Cocitation <-- [DS]
- [x] Components <-- [AG]
- [ ] Communities [DS]
- [ ] Configuration model [DS]
- [x] Degree distribution [AG]
- [x] Diameter [AG]
- [ ] Diffusion <-- [AG]
- [ ] Flow <-- [AG]
- [ ] Motifs
- [ ] Percolation <-- [DS]
- [ ] Random networks <-- [DS]
- [ ] Sampling <-- [AG]
- [ ] SIR/Cascade (N/A)
- [x] Trees <-- [AG] (Very much not a tree)
- [x] Visualization <-- [AG]
- [ ] Others

## Todo

- [ ] Add edges to nodes based on real world distance to reflect walking
  traversability. Only add edges based on a threshold to not destroy our
  computers with math.
    - Period of waiting between bus stops
- [ ] Analyze travel time variance over times of the course of a day
- [ ] Investigate Google API (optional)
