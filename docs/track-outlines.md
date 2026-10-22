# Track outlines

Circuit outlines and landmark backgrounds for the Web telemetry map, built offline on the AI box
from OpenStreetMap and published as release assets. The Server serves them; it no longer has to ask
the public Overpass instances, which refuse or time out under automated load.

## Build

```sh
python3 scripts/track_outlines.py lines --g61 <garage61 root> --catalogue catalogue.json --out lines/
python3 scripts/osm_extract.py plan --catalogue catalogue.json --lines lines/ --index index-v1.json --out plan.json
python3 scripts/osm_extract.py download --plan plan.json --out pbf/
python3 scripts/osm_extract.py extract --plan plan.json --pbf pbf/ --out osm/      # needs pyosmium
python3 scripts/track_outlines.py build --catalogue catalogue.json --lines lines/ --osm osm/ --out out/
```

- `catalogue.json` is the list `{id, name, config, lat, lon, length}` read from the Server's cached iRacing
  track catalogue.
- **Line.** One reference line per track: the medoid closed lap of the Garage 61 laps of that track and
  configuration, matched by name. Only the derived 5 m line is kept: no driver names, lap ids or raw rows.
- **OSM.** `plan` picks the smallest Geofabrik region for each corner and the centre of the track area,
  which is the line's bounding box plus 4 km. A track on a border uses two regions. `download` resumes and
  skips a file whose Geofabrik MD5 is unchanged.
- **Alignment.** iRacing's Lat/Lon is rotated or shifted against the real world at some tracks (Le Mans
  −0.55°, up to 55 m). The build fits a similarity from the line onto parallel OSM roads, with ICP and the
  scale clamped to 1 ± 0.003. It then selects the drivable ways (raceway and public roads) within 15 m of
  the aligned line, parallel to it and at least 40 m long, and stitches one outline along the line. A
  sample with no OSM way within 15 m keeps the line itself.
- **Pit lane.** Ways tagged `raceway=pitlane` or `service=pit`, or named pit lane, entry or exit, near the
  circuit.
- **Frame.** Everything is moved back into iRacing's frame, where the laps are drawn.

## Output (format 1)

| File | Contents |
|---|---|
| `<id>.circuit.json` | `outline` (closed [lat, lon] ring), `pit` (polylines), `quality`, attribution |
| `<id>.background.json` | landmark `ways` (`kind` as in the Server's background contract), attribution |

Each file also carries `track_id`, `built_at`, `line_source`, `line_laps`, `osm_timestamp`.

`quality` holds:

- `aligned`
- `coverage`: share of the lap with an OSM way
- `coverage_unaligned`
- `median_m` and `p90_m`: line to outline
- `rotation_deg`, `scale`, `shift_m` and `max_shift_m`: the fitted iRacing-to-OSM transform
- `lap_m`
- `osm_ways`

OSM data © OpenStreetMap contributors, ODbL 1.0. The outputs are a derived database under the same
licence and must keep the attribution.
