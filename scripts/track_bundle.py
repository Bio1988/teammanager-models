#!/usr/bin/env python3
"""Package built track outlines as one release.

  track_bundle.py --built out/ --version <v> --commit <sha> --catalogue catalogue.json --lines lines/ \
      [--previous provenance.json] --out release/

writes track-outlines-<v>.zip (circuit/<id>.json, background/<id>.json, quality.json, NOTICE.txt; byte-reproducible:
fixed member order and timestamps), needs-line.json, SHA256SUMS (both files) and provenance.json. With --previous
(the last release's provenance.json) it refuses a release that loses a track or a track's turns.
Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from track_outlines import ATTRIBUTION, FORMAT, LICENSE

NOTICE = """Track outlines for the TeamManager telemetry map.

Map data (c) OpenStreetMap contributors, available under the Open Database License 1.0
(https://opendatacommons.org/licenses/odbl/1-0/, https://www.openstreetmap.org/copyright).
These files are a derived database of that data and are offered under the same licence.

Reference lines are derived from Garage 61 lap telemetry (line_source "garage61") or from
TeamManager users' own .ibt imports (line_source "ibt"); only a 5 m resampled line was used,
no driver names, lap ids or raw rows. Coordinates are in iRacing's own Lat/Lon frame. Where
OpenStreetMap has no way (quality label "line", "mixed" or "fictional") the outline is that line.

Turn numbers come from iRacing's public track maps (turns.svg, fitted with active.svg; each
circuit file's turns_source names the files, their sha256 and fetch time). They are iRacing's
labels placed by a fit and filtered for lap order, not an official iRacing data product.
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def needs_line(catalogue, built, tracks, line_ids):
    """What to drive (or fetch laps for): tracks without an outline, and tracks whose outline is partly the line
    because OSM covers less than 90 %; an own .ibt lap of such a track becomes its line."""
    coverage = {}
    for tid in tracks:
        q = json.loads((built / f"{tid}.circuit.json").read_text())["quality"]
        coverage[tid] = 1.0 if q["label"] == "fictional" else q["coverage"]  # no real place: nothing to drive for
    entry = lambda t, reason: {"track_id": t["id"], "track": t["name"], "layout": t["config"] or "", "reason": reason}
    needs = [entry(t, "reference line exists, OSM extract missing" if t["id"] in line_ids else "no reference line")
             for t in catalogue if t["id"] not in coverage]
    needs += [entry(t, f"OSM covers {coverage[t['id']]:.0%}, the rest of the outline is the reference line")
              for t in catalogue if coverage.get(t["id"], 1.0) < 0.9]
    return sorted(needs, key=lambda n: (n["track"], n["layout"]))


def cmd_bundle(args):
    built, out = Path(args.built), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"track-outlines-{args.version}.zip"
    tracks, with_turns, sources, regions, built_at = [], [], defaultdict(int), set(), ""
    members, content, labels, svgs = [], hashlib.sha256(), defaultdict(int), []
    for f in sorted(built.glob("*.circuit.json"), key=lambda p: int(p.name.split(".")[0])):
        tid = int(f.name.split(".")[0])
        circuit = json.loads(f.read_text())
        labels[circuit["quality"]["label"]] += 1
        tracks.append(tid)
        if circuit.get("turns"):
            with_turns.append(tid)
        svgs += [{"track_id": tid, "layer": kind, **src} for kind, src in sorted((circuit.get("turns_source") or {}).items())]
        sources[circuit["line_source"]] += 1
        regions.add(circuit.get("osm_timestamp") or "")
        built_at = max(built_at, circuit["built_at"])
        bg = (built / f"{tid}.background.json").read_bytes()
        members += [(f"circuit/{tid}.json", f.read_bytes()), (f"background/{tid}.json", bg)]
        for doc in (circuit, json.loads(bg)):  # geometry only: a new OSM snapshot without changes is no new release
            content.update(json.dumps({k: v for k, v in doc.items() if k not in ("built_at", "osm_timestamp", "turns_source")},
                                      sort_keys=True).encode())
    if not tracks:
        raise SystemExit(f"bundle: no built track in {built}; nothing to release")
    if args.previous:
        previous = json.loads(Path(args.previous).read_text())
        lost = sorted(set(previous["tracks"]) - set(tracks))
        lost_turns = sorted(set(previous.get("tracks_with_turns", [])) - set(with_turns))
        if lost or lost_turns:
            raise SystemExit(f"bundle: against the previous release, tracks lost {lost}, turns lost {lost_turns}")
    members += [("quality.json", (built / "quality.json").read_bytes()), ("NOTICE.txt", NOTICE.encode())]
    with ZipFile(out / name, "w", ZIP_DEFLATED) as z:
        for arc, data in members:
            info = ZipInfo(arc, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, data)
    line_ids = {int(p.name.split(".")[0]) for p in Path(args.lines).glob("*.line.json")} if args.lines else set()
    needs = needs_line(json.loads(Path(args.catalogue).read_text()), built, tracks, line_ids)
    (out / "needs-line.json").write_text(json.dumps(needs, indent=1, ensure_ascii=False) + "\n")
    digest, needs_digest = sha256((out / name).read_bytes()), sha256((out / "needs-line.json").read_bytes())
    (out / "SHA256SUMS").write_text(f"{digest}  {name}\n{needs_digest}  needs-line.json\n")
    (out / "provenance.json").write_text(json.dumps({
        "asset": name, "sha256": digest, "content_sha256": content.hexdigest(), "size": (out / name).stat().st_size, "format": FORMAT,
        "built_at": built_at, "builder_commit": args.commit, "tracks": tracks, "tracks_with_turns": with_turns,
        "labels": dict(sorted(labels.items())),
        "line_sources": dict(sorted(sources.items())),
        "needs_line": {"asset": "needs-line.json", "sha256": needs_digest, "entries": len(needs)},
        "osm": {"source": "Geofabrik regional extracts", "timestamps": sorted(regions - {""}),
                "attribution": ATTRIBUTION, "license": LICENSE},
        "iracing_track_maps": {"source": "iRacing public track-map SVGs (turn labels)", "files": svgs},
    }, indent=1) + "\n")
    print(f"{name} {digest} {len(tracks)} tracks, {len(with_turns)} with turns", file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--built", required=True, help="output directory of track_outlines.py build (+ track_turns.py place)")
    p.add_argument("--version", required=True)
    p.add_argument("--commit", required=True, help="builder git commit")
    p.add_argument("--out", required=True)
    p.add_argument("--catalogue", required=True, help="for needs-line.json: catalogue tracks without an outline")
    p.add_argument("--lines", default="", help="reference lines, to tell a missing OSM extract from a missing line")
    p.add_argument("--previous", default="", help="the last release's provenance.json: refuse to lose tracks or turns")
    cmd_bundle(p.parse_args(argv))


if __name__ == "__main__":
    main()
