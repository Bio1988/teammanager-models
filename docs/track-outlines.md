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
python3 scripts/track_turns.py fetch --catalogue catalogue.json --out svg/                     # conditional GET after 6 days
python3 scripts/track_turns.py place --built out/ --lines lines/ --svg svg/                    # needs svgelements
python3 scripts/track_bundle.py --built out/ --version <yyyymmdd> --commit <builder sha> --catalogue catalogue.json \
  --lines lines/ --previous <last release provenance.json> --out release/
```

- `catalogue.json` is the list `{id, name, config, lat, lon, length, track_map, layers}` read from the
  Server's cached iRacing track catalogue (`track_map` is the track-map folder on iRacing's public CDN,
  `layers` its file names).
- **Line.** One reference line per track: the medoid of the agreeing closed Garage 61 laps of that
  track and configuration (at least two for a loose match below). Sources: `telemetry/`, `telemetry-pro/`, `telemetry-pairs/` and
  `sessions-dirt/` (a lap saved in several folders counts once); names come from `laps.csv`,
  `pro_laps.csv` and `_missing_laps.csv`. Names match exactly; a `[Retired]`/`[Legacy]` catalogue entry
  without an exact match falls back to the plain name, but never to a G61 track that an exact catalogue
  entry claims (those laps are the current layout) and only when the lap length matches the catalogue's
  (6 %) and two laps agree. A line from the user's own `.ibt` import (`source: "ibt"`, derived from the Server's import
  blocks outside this script) already in the output directory is kept. Only the derived 5 m line is
  kept: no driver names, lap ids or raw rows.
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
  sample with no OSM way within 15 m keeps the line itself, so every track with a line gets a whole outline:
  `quality.sources` lists the `[from_pct, to_pct, "osm" | "line"]` runs along the lap and `quality.label`
  says `osm` (at least 90 % OSM), `mixed` (50–90 %), `line` (under 50 %, mostly dirt, rallycross and closed
  layouts OSM does not map) or `fictional`. `width_m` is the band width for the line parts: twice the
  laps' p90 lateral spread plus 4 m (8–30 m) with three laps or more, else 12 m. If the main roads do not
  give a fit (Mount Panorama runs on residential roads), the fit is retried on every drivable way.
- **Fictional tracks.** The iRacing Superspeedway is no real place: it is built from the line alone,
  without OSM ways or background, and labelled `fictional`.
- **Turns.** `track_turns.py` fits iRacing's own track map (`active.svg`) onto the reference line (coarse
  rotation search, then ICP with a similarity, as the Web map does) and places each `turns.svg` label (the
  text of a `<text>` with its spans joined) on the nearest sample of the closed line: `turns: [{number,
  label, apex_pct}]` in lap order, `apex_pct` measured along the lap from the start/finish line like
  `LapDistPct`. Only labels like `3`, `3a` or `T14` are turns (not `100R`, `180º`, `TV3` or words); a
  label twice at the same place counts once. Neighbouring labels in the wrong number order within 200 m
  (chicanes) take their numbers in order; a track whose labels still break the lap order more than twice,
  or whose fit has a two-sided mean error over 30 m, gets no turns. `turns_fit` records the error, the
  transform and the inversions before and after; `turns_source` names both SVGs (URL, SHA-256, fetch time).
  These are iRacing's labels placed by a fit, not official iRacing data.
- **No imagery.** Missing roads are filled from the driven line, not traced from aerial images:
  commercial imagery (Esri, Google, Bing) may not be used to derive geometry outside OSM editing. Openly
  licensed alternatives exist but are not used: Sentinel-2 (Copernicus, free and open, 10 m pixels, too
  coarse for track edges), NAIP (US public domain, about 0.6 m, US only) and OpenAerialMap (per-image
  licences, often CC BY).
- **Pit lane.** Ways tagged `raceway=pitlane` or `service=pit`, or named pit lane, entry or exit, near the
  circuit.
- **Frame.** Everything is moved back into iRacing's frame, where the laps are drawn.

## Release

`track_bundle.py` writes `track-outlines-<version>.zip` (`circuit/<id>.json`, `background/<id>.json`,
`quality.json`, `NOTICE.txt`; byte-reproducible; every built track ships, its `quality.label` says how
much is OSM), `needs-line.json` (`{track_id, track, layout, reason}` sorted by name: tracks without a reference line,
and tracks whose outline is partly the line because OSM covers under 90 %; the list for driving or
fetching laps), `SHA256SUMS` and `provenance.json` (asset hash,
`content_sha256` over the geometry only, build time, builder commit, track ids, tracks with turns,
labels, line sources, OSM snapshot times, the `needs-line.json` hash, every iRacing SVG used, attribution);
`SHA256SUMS` lists the zip and `needs-line.json`. With `--previous` it refuses a release that loses a track
or a track's turns. Line-only and fictional outlines name the lap source (Garage 61 or the user's .ibt)
as attribution instead of OSM. They are published as the Forgejo release `track-outlines-<version>`.
The Server pins one release by URL and SHA-256; a newer release changes nothing until that pin moves.

## Automatic rebuilds

`.forgejo/workflows/track-outlines.yml` runs on the `ai-box` runner:

- **Daily, incremental** (02:47 UTC, not Mondays): catalogue tracks with a reference line that the latest
  release lacks (`track_release.py new-ids`) are planned, extracted, built and given turns, then added to the
  latest release's files (`unpack`, `merge`). Without a new track the run stops after the check.
- **Mondays, full** (01:17 UTC): every track from fresh Geofabrik extracts (one region after another,
  unchanged files skipped by MD5) and re-checked SVGs (conditional GET after 6 days).
- `workflow_dispatch` with `mode` `full` or `incremental`.

The catalogue comes from the Server's public `GET /api/v1/public/track-catalogue` (last good copy kept when
it cannot be read). A release is published only when `content_sha256` changed, never loses a track or a
track's turns (`track_bundle.py --previous`), and is created as a draft, gets all assets and is then
published; a failure deletes the draft and its tag. A second release on one day gets an `-HHMM` suffix. The
Server finds the newest release by itself (weekly, through Forgejo's releases API) and checks it against
`SHA256SUMS`, the size cap and the same superset rule.

The job runs on the `ai-box` runner label, which the AI box runner registers as `ai-box:host`: jobs run
directly in the runner container, which pull-request jobs of every repository share. State therefore lives
on the host in `/workspace/track-outlines` (the runner's bind mount), outside any job's work tree:

- `lines/`: `<id>.line.json` from the `lines` step (Garage 61) or from an own `.ibt` lap; seeded by the
  operator, since the Garage 61 data is not on the runner. A track gets an outline once it has a line here.
- `pbf/`, `svg/`, `venv/`: kept between runs; `catalogue.json`, `plan.json`, `cut/`, `out/`, `previous/`,
  `release/` are rewritten by each run.

## Output (format 1)

| File | Contents |
|---|---|
| `<id>.circuit.json` | `outline` (closed [lat, lon] ring), `pit` (polylines), `width_m`, `turns`, `turns_fit`, `quality`, attribution |
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
- `sources` and `label` (see Alignment)

OSM data © OpenStreetMap contributors, ODbL 1.0. The outputs are a derived database under the same
licence and must keep the attribution.
