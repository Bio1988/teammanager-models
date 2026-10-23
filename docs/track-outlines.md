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
python3 scripts/track_outlines.py bundle --built out/ --version <yyyymmdd> --commit <builder sha> --out release/
```

- `catalogue.json` is the list `{id, name, config, lat, lon, length}` read from the Server's cached iRacing
  track catalogue.
- **Line.** One reference line per track: the medoid closed lap of the Garage 61 laps of that track and
  configuration, matched by name. Only the derived 5 m line is kept: no driver names, lap ids or raw rows.
- **OSM.** `plan` picks the smallest Geofabrik region for each corner and the centre of the track area,
  which is the line's bounding box plus 4 km. A track on a border uses two regions. `download` resumes and
  skips a file whose Geofabrik MD5 is unchanged.
- **Alignment.** iRacing's Lat/Lon is rotated or shifted against the real world at some tracks (Le Mans
  −0.58°, up to 56 m; Imola −1.03°, up to 39 m). The build fits a similarity from the line onto parallel OSM roads, with ICP and the
  scale clamped to 1 ± 0.003. A fit that rotates more than 2° or moves a point more than 100 m matched the
  wrong roads and is dropped (the track stays unaligned). If that fit fails, a coarse translation search (up to 600 m, 10 m steps) finds the frame offset first, but only when roads
  carry 60 % of the lap, at least 60 % of samples land on a parallel road and twice as many as at zero offset; the same ICP and
  rotation limit apply and the finished outline must reach 90 % OSM coverage, else the track stays unaligned (Wild West, about
  480 m off, does not). It then selects the drivable ways (raceway, public roads,
  service roads and parking aisles, pedestrian ways, `highway=track`, airport runways and taxiways, and ways OSM keeps only
  as `disused:highway=raceway`, as at St. Petersburg) within 15 m of
  the aligned line, parallel to it and at least 40 m long, and stitches one outline along the line. A
  sample with no OSM way within 15 m keeps the line itself.
- **Pit lane.** Ways tagged `raceway=pitlane` or `service=pit`, or named pit lane, entry or exit, near the
  circuit.
- **Frame.** Everything is moved back into iRacing's frame, where the laps are drawn.

## Release

`bundle` writes `track-outlines-<version>.zip` (`circuit/<id>.json`, `background/<id>.json`,
`quality.json`, `NOTICE.txt`; byte-reproducible; tracks under 90 % OSM coverage are left out so the
Server keeps its fallback for them), `SHA256SUMS` and `provenance.json` (asset hash,
`content_sha256` over the geometry only, build time, builder commit, track ids, line sources, OSM
snapshot times, attribution). They are published as the Forgejo release `track-outlines-<version>`.
The Server pins one release by URL and SHA-256; a newer release changes nothing until that pin moves.

## Weekly rebuild

`.forgejo/workflows/track-outlines.yml` runs on the `ai-box` runner every Monday at 01:17 UTC (and on
dispatch): Geofabrik index, plan, sequential downloads (unchanged files skipped by MD5), extract, build,
bundle. It publishes a new release only when `content_sha256` differs from the latest
`track-outlines-*` release, and refuses when a track of that release is missing. The release is created as a
draft, gets all assets and is then published; a failure deletes the draft and its tag.

The job runs on the `ai-box` runner label, which the AI box runner registers as `ai-box:host`: jobs run
directly in the runner container, which pull-request jobs of every repository share. State therefore lives
on the host in `/workspace/track-outlines` (the runner's bind mount), outside any job's work tree:

- `catalogue.json`: `{id, name, config, lat, lon, length}` per catalogue track, exported read-only from
  the Server's cached iRacing catalogue. Re-export it to pick up new tracks.
- `lines/`: `<id>.line.json` from the `lines` step (Garage 61) or from an own `.ibt` lap.
- `pbf/`, `venv/`: kept between runs.

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
