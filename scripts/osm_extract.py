#!/usr/bin/env python3
"""Cut the OSM elements around each iRacing track out of Geofabrik regional extracts.

  plan      catalogue + reference lines -> track areas and the smallest Geofabrik region holding each
  download  fetch the planned region .osm.pbf files one after another (resumes, skips unchanged by MD5)
  extract   one pass per region -> <track_id>.<region>.osm.json in the shape of Overpass `out geom` JSON, which
            track_outlines.py build reads

`plan` and `download` use the standard library only; `extract` needs pyosmium (`pip install osmium`).
Geofabrik serves OpenStreetMap data under the ODbL; every derived file keeps that attribution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "TeamManager-track-outlines/1 (circuit outline builder)"
INDEX_URL = "https://download.geofabrik.de/index-v1.json"
PAD_M = 4000.0       # around the reference line: circuit plus the landmark background
NO_LINE_PAD_M = 8000.0
M_PER_DEG = 111_320.0

CIRCUIT_KEYS = ("highway", "area:highway", "raceway")
BG_KEYS = ("bridge", "power", "barrier", "building", "amenity", "natural", "landuse")
KEEP_TAGS = ("name", "highway", "area:highway", "raceway", "service", "surface", "width", "bridge", "power",
             "barrier", "building", "amenity", "natural", "landuse")


def bbox_of(points, pad_m):
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    dlat = pad_m / M_PER_DEG
    dlon = pad_m / (M_PER_DEG * math.cos(math.radians(sum(lats) / len(lats))))
    return [min(lats) - dlat, min(lons) - dlon, max(lats) + dlat, max(lons) + dlon]


def inside(lat, lon, multipolygon) -> bool:
    """Even-odd ray test over all rings of a GeoJSON MultiPolygon ([lon, lat] order)."""
    hit = False
    for polygon in multipolygon:
        for ring in polygon:
            for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
                if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                    hit = not hit
    return hit


def ring_area(multipolygon) -> float:
    return sum(abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:]))) / 2
               for polygon in multipolygon for r in polygon[:1])


def cmd_plan(args):
    catalogue = json.loads(Path(args.catalogue).read_text())
    index = json.loads(Path(args.index).read_text())["features"]
    regions = [(ring_area(f["geometry"]["coordinates"]), f) for f in index
               if f.get("geometry") and f["geometry"]["type"] == "MultiPolygon" and f["properties"]["urls"].get("pbf")]
    regions.sort(key=lambda r: r[0])
    wanted = set(map(int, args.ids.split(","))) if args.ids else None
    areas, plan, missing = {}, {}, []
    for t in catalogue:
        if wanted and t["id"] not in wanted:
            continue
        lf = Path(args.lines) / f"{t['id']}.line.json"
        if lf.exists():
            box = bbox_of(json.loads(lf.read_text())["line"], PAD_M)
        else:
            box = bbox_of([(t["lat"], t["lon"])], NO_LINE_PAD_M)
        # every corner and the centre goes to the smallest region holding it; a track on a border needs two
        points = [(box[0], box[1]), (box[0], box[3]), (box[2], box[1]), (box[2], box[3]), ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)]
        rids = set()
        for a, b in points:
            region = next((f for _, f in regions if inside(a, b, f["geometry"]["coordinates"])), None)
            if region:
                rids.add(region["properties"]["id"])
                plan.setdefault(region["properties"]["id"], {"url": region["properties"]["urls"]["pbf"], "tracks": []})
        if not rids:
            missing.append(t["id"])
            continue
        areas[t["id"]] = {"bbox": [round(v, 6) for v in box], "regions": sorted(rids)}
        for rid in rids:
            plan[rid]["tracks"].append(t["id"])
    Path(args.out).write_text(json.dumps({"areas": areas, "regions": plan}, indent=1))
    print(f"{len(areas)} tracks in {len(plan)} regions; no region: {missing}", file=sys.stderr)


def md5_of(path: Path) -> str:
    md5 = hashlib.md5()
    with path.open("rb") as f:
        while chunk := f.read(1 << 24):
            md5.update(chunk)
    return md5.hexdigest()


def pbf_name(rid: str) -> str:
    """Local file of a Geofabrik region id; ids such as `us/alabama` hold a slash."""
    return rid.replace("/", "-") + ".osm.pbf"


class _KeepMethod(urllib.request.HTTPRedirectHandler):
    """urllib turns a redirected HEAD into a GET, which would start the whole download; keep the method."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        return new and urllib.request.Request(new.full_url, headers=dict(new.header_items()), method=req.get_method())


_opener = urllib.request.build_opener(_KeepMethod)


def _get(url: str, method: str = "GET", headers=None):
    return _opener.open(urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT, **(headers or {})}), timeout=120)


def fetch(url: str, dest: Path, pause: float = 30.0):
    """Download with resume; the .md5 Geofabrik publishes decides whether a file is current.

    Geofabrik answers `<region>-latest.osm.pbf` with a redirect to the dated file (`<region>-261020.osm.pbf`).
    The dated URL is resolved once, so the file and its .md5 come from the same snapshot, and a partial
    download is resumed only against the same dated file."""
    with _get(url, "HEAD") as r:
        final = r.geturl()  # urllib follows 301/302/303/307/308
    want = _get(final + ".md5").read().split()[0].decode()
    if dest.exists() and md5_of(dest) == want:
        return "current"
    part, source = dest.with_name(dest.name + ".part"), dest.with_name(dest.name + ".part-url")
    if part.exists() and (not source.exists() or source.read_text() != final):
        part.unlink()  # started on another snapshot
    source.write_text(final)
    for attempt in range(5):
        have = part.stat().st_size if part.exists() else 0
        try:
            with _get(final, headers={"Range": f"bytes={have}-"} if have else None) as r, part.open("ab" if have and r.status == 206 else "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            break
        except urllib.error.HTTPError as e:
            if e.code == 416 and have:  # already complete; the MD5 below decides
                break
            err = e
        except OSError as e:
            err = e
        print(f"  retry {attempt + 1} after {err}", file=sys.stderr)
        time.sleep(pause * (attempt + 1))
    else:
        raise RuntimeError(f"download failed: {final}")
    if md5_of(part) != want:
        part.unlink()
        raise RuntimeError(f"md5 mismatch: {final}")
    part.replace(dest)
    source.unlink()
    return "downloaded"


def cmd_download(args):
    plan = json.loads(Path(args.plan).read_text())["regions"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for rid in sorted(plan):
        dest = out / pbf_name(rid)
        print(rid, fetch(plan[rid]["url"], dest), dest.stat().st_size, file=sys.stderr, flush=True)
        time.sleep(args.pause)


def cmd_extract(args):
    import osmium  # pyosmium; only this step needs it

    plan = json.loads(Path(args.plan).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    regions = [args.region] if args.region else sorted(plan["regions"])
    for rid in regions:
        tracks = [t for t in plan["regions"][rid]["tracks"] if not args.ids or str(t) in args.ids.split(",")]
        if not tracks:
            continue
        boxes = {t: plan["areas"][str(t)]["bbox"] for t in tracks}
        pbf = Path(args.pbf) / pbf_name(rid)
        t0 = time.time()
        within = lambda lat, lon: [t for t, b in boxes.items() if b[0] <= lat <= b[2] and b[1] <= lon <= b[3]]
        coords, elements = {}, {t: [] for t in tracks}
        wanted = lambda tags: any(k in tags for k in CIRCUIT_KEYS + BG_KEYS)
        for obj in osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY):
            if obj.is_node():
                loc = obj.location
                if not loc.valid():
                    continue
                lat, lon = loc.lat, loc.lon
                if within(lat, lon):
                    coords[obj.id] = (round(lat, 7), round(lon, 7))
                    tags = dict(obj.tags)
                    if tags.get("natural") == "tree" or tags.get("power") in ("tower", "pole"):
                        for t in within(lat, lon):
                            elements[t].append({"type": "node", "id": obj.id, "lat": lat, "lon": lon,
                                                 "tags": {k: tags[k] for k in KEEP_TAGS if k in tags}})
            elif obj.is_way():
                if not wanted(obj.tags):
                    continue
                pts = [coords[n.ref] for n in obj.nodes if n.ref in coords]
                if len(pts) < 2:
                    continue
                tags = {k: obj.tags[k] for k in KEEP_TAGS if k in obj.tags}
                hit = set()
                for lat, lon in pts:
                    hit.update(within(lat, lon))
                for t in hit:
                    elements[t].append({"type": "way", "id": obj.id, "tags": tags,
                                        "geometry": [{"lat": a, "lon": b} for a, b in pts]})
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(pbf.stat().st_mtime))
        for t in tracks:
            (out / f"{t}.{rid.replace('/', '-')}.osm.json").write_text(json.dumps({"region": rid, "osm_timestamp": stamp, "elements": elements[t]},
                                                          separators=(",", ":"), ensure_ascii=False))
        print(f"{rid}: {len(tracks)} tracks, {len(coords)} nodes kept, {time.time() - t0:.0f} s", file=sys.stderr, flush=True)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("plan")
    a.add_argument("--catalogue", required=True)
    a.add_argument("--lines", required=True)
    a.add_argument("--index", required=True, help=f"Geofabrik {INDEX_URL}")
    a.add_argument("--out", required=True)
    a.add_argument("--ids", default="")
    a.set_defaults(fn=cmd_plan)
    b = sub.add_parser("download")
    b.add_argument("--plan", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--pause", type=float, default=5.0)
    b.set_defaults(fn=cmd_download)
    c = sub.add_parser("extract")
    c.add_argument("--plan", required=True)
    c.add_argument("--pbf", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--region", default="")
    c.add_argument("--ids", default="")
    c.set_defaults(fn=cmd_extract)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
