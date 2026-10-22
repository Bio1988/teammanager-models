#!/usr/bin/env python3
"""Build GPS-aligned circuit outlines for iRacing tracks from OpenStreetMap ways.

Standard library only. Two steps, each a subcommand:

  lines   Garage 61 lap CSVs -> one reference line per iRacing track (the medoid lap,
          5 m spacing, iRacing's own Lat/Lon frame). Only derived geometry is written:
          no driver names, lap ids or raw rows.
  build   reference line + OSM elements of the track area (Overpass `out geom` JSON shape)
          -> <id>.circuit.json (stitched outline, pit lane, quality) and
             <id>.background.json (landmarks), both in iRacing's frame.

iRacing's Lat/Lon is a local model frame: at some tracks it is rotated or shifted against
the real world (Le Mans -0.54 deg, up to 50 m on the far side). The build therefore fits a
similarity (rotation, shift, scale clamped near 1) from the line onto parallel OSM roads,
selects the circuit in the aligned frame and moves everything back into iRacing's frame,
where the laps are drawn.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ATTRIBUTION = "© OpenStreetMap contributors"
LICENSE = "ODbL-1.0"
FORMAT = 1
M_PER_DEG = 111_320.0

STEP_M = 5.0          # reference line spacing
KEEP_M = 15.0         # an OSM point this close to the aligned line is on the circuit
MIN_RUN_M = 40.0      # shorter on-line runs (crossing roads, bridges) are dropped
MAX_ANGLE = 30.0      # deg between a run and the line
FIT_STEPS = (80.0, 60.0, 40.0, 25.0) + (15.0,) * 30  # nearest-point ICP slides slowly along straights
FIT_ANGLE = 25.0
SCALE_LIMIT = 0.003   # the racing line cuts corners, so a free scale fit is biased
PIT_END_M = 50.0     # a pit lane joins the circuit: both ends of a pit way lie this close to the line
PIT_MEDIAN_M = 40.0  # and it runs alongside it (another layout's pit lane does not)

DRIVABLE = {"raceway", "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
            "service", "road", "living_street", "motorway_link", "trunk_link", "primary_link", "secondary_link",
            "tertiary_link"}
FIT_ROADS = DRIVABLE - {"service", "residential", "living_street"}
PIT_NAME = re.compile(r"^(pit ?lane|pit entry|pit exit|pit road|boxengasse)$", re.I)

# Background kinds in keep order with per-kind caps (the Server's former bgKinds).
BG_KINDS = [("bridge", 50), ("power_line", 100), ("power_tower", 300), ("kerb", 300), ("barrier", 400),
            ("grandstand", 100), ("building", 800), ("parking", 150), ("tree_row", 150), ("area:water", 150),
            ("area:forest", 150), ("area:grass", 150), ("area:scrub", 100), ("area:farmland", 100), ("tree", 1000)]
BG_MAX_POINTS = 30_000
BG_RADIUS_M = 4000.0


# ---------------------------------------------------------------- geometry helpers

class Frame:
    """Local equirectangular metres around an origin: x east, y north."""

    def __init__(self, lat: float, lon: float):
        self.lat, self.lon, self.k = lat, lon, math.cos(math.radians(lat))

    def xy(self, lat: float, lon: float) -> tuple[float, float]:
        return (lon - self.lon) * M_PER_DEG * self.k, (lat - self.lat) * M_PER_DEG

    def ll(self, p) -> list[float]:
        return [round(p[1] / M_PER_DEG + self.lat, 7), round(p[0] / (M_PER_DEG * self.k) + self.lon, 7)]


def length(pts) -> float:
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def resample(pts, step: float):
    """Points every `step` metres along the polyline (first point kept)."""
    if len(pts) < 2:
        return list(pts)
    out, carry = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.dist(a, b)
        t = step - carry
        while t <= seg:
            f = t / seg
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            t += step
        carry = (carry + seg) % step if seg else carry
    return out


def tangents(pts):
    out = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        d = math.dist(a, b) or 1.0
        out.append(((b[0] - a[0]) / d, (b[1] - a[1]) / d))
    return out


class Grid:
    """Hash grid over points with an index payload, for nearest-point queries within a radius."""

    def __init__(self, pts, cell: float):
        self.pts, self.cell, self.cells = pts, cell, defaultdict(list)
        for i, (x, y) in enumerate(pts):
            self.cells[(int(x // cell), int(y // cell))].append(i)

    def near(self, p, radius: float, accept=None):
        """(distance, index) of the nearest accepted point within radius, or (inf, -1)."""
        r = int(radius // self.cell) + 1
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        best = (math.inf, -1)
        for gx in range(cx - r, cx + r + 1):
            for gy in range(cy - r, cy + r + 1):
                for i in self.cells.get((gx, gy), ()):
                    d = math.dist(p, self.pts[i])
                    if d < best[0] and d <= radius and (accept is None or accept(i)):
                        best = (d, i)
        return best


def similarity(src, dst, scale_limit=SCALE_LIMIT):
    """Closed-form 2D least-squares similarity src -> dst as (a, b, tx, ty): x' = a x - b y + tx, y' = b x + a y + ty."""
    n = len(src)
    mx, my = sum(p[0] for p in src) / n, sum(p[1] for p in src) / n
    nx, ny = sum(p[0] for p in dst) / n, sum(p[1] for p in dst) / n
    dot = cross = norm = 0.0
    for (x, y), (u, v) in zip(src, dst):
        px, py, qx, qy = x - mx, y - my, u - nx, v - ny
        dot += px * qx + py * qy
        cross += px * qy - py * qx
        norm += px * px + py * py
    a, b = dot / norm, cross / norm
    s = math.hypot(a, b)
    c = min(max(s, 1 - scale_limit), 1 + scale_limit) / s
    a, b = a * c, b * c
    return a, b, nx - (a * mx - b * my), ny - (b * mx + a * my)


def apply(m, p):
    a, b, tx, ty = m
    return a * p[0] - b * p[1] + tx, b * p[0] + a * p[1] + ty


def invert(m):
    a, b, tx, ty = m
    d = a * a + b * b
    ia, ib = a / d, -b / d
    return ia, ib, -(ia * tx - ib * ty), -(ib * tx + ia * ty)


def percentile(values, q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(round(q / 100 * (len(s) - 1))))] if s else math.nan


# ---------------------------------------------------------------- lines (Garage 61)

def norm_name(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).casefold()


def read_lap(path: Path):
    """Lat/Lon of one G61 lap CSV (header row, unit row, samples)."""
    with path.open(newline="") as f:
        rows = csv.reader(f)
        head = next(rows)
        next(rows, None)
        ilat, ilon = head.index("Lat"), head.index("Lon")
        out = []
        for r in rows:
            try:
                lat, lon = float(r[ilat]), float(r[ilon])
            except (ValueError, IndexError):
                continue
            if lat or lon:
                out.append((lat, lon))
    return out


def medoid_line(laps_ll, max_laps=12):
    """The closed lap closest to all others (median distance), resampled to STEP_M, plus how many laps agreed.

    Partial laps (out laps, cut recordings) do not close on themselves and are dropped; so are laps with a
    sample jump over 50 m (tow, teleport) and laps more than 3 % off the median closed-lap length."""
    frame = Frame(*laps_ll[0][0])
    laps = []
    for lap in laps_ll:
        pts = [frame.xy(*p) for p in lap]
        if len(pts) < 100 or math.dist(pts[0], pts[-1]) > 100 or any(math.dist(a, b) > 50 for a, b in zip(pts, pts[1:])):
            continue
        r = resample(pts, STEP_M)
        if len(r) * STEP_M >= 300:
            laps.append(r)
    if not laps:
        return None, 0
    med = statistics.median_low(len(l) for l in laps)
    laps = [l for l in laps if abs(len(l) - med) <= 0.03 * med][:max_laps]
    best, best_score = laps[0], math.inf
    for i, lap in enumerate(laps):
        others = [l for j, l in enumerate(laps) if j != i]
        if not others:
            break
        score = statistics.median(dist_to_line(lap[::4], o) for o in others)
        if score < best_score:
            best, best_score = lap, score
    return [frame.ll(p) for p in best], len(laps)


def dist_to_line(pts, line):
    g = Grid(line, 10.0)
    ds = [g.near(p, 60.0)[0] for p in pts]
    return statistics.median(ds)


def g61_index(root: Path):
    """G61 track id -> (track, variant) from the lap indexes (names of drivers are never read)."""
    names = {}
    for idx in (root / "telemetry" / "laps.csv", root / "telemetry-pro" / "pro_laps.csv"):
        if idx.exists():
            with idx.open(newline="") as f:
                for r in csv.DictReader(f):
                    names.setdefault(r["track_id"], (r["track"], r.get("track_variant") or ""))
    return names


def cmd_lines(args):
    root = Path(args.g61)
    catalogue = json.loads(Path(args.catalogue).read_text())
    by_name = defaultdict(list)
    for gid, (track, variant) in g61_index(root).items():
        by_name[(norm_name(track), norm_name(variant))].append(gid)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(map(int, args.ids.split(","))) if args.ids else None
    report = []
    for t in sorted(catalogue, key=lambda t: t["id"]):
        if wanted and t["id"] not in wanted:
            continue
        gids = by_name.get((norm_name(t["name"]), norm_name(t["config"])), [])
        files = [p for gid in gids for d in ("telemetry", "telemetry-pro", "telemetry-pairs")
                 for p in sorted((root / d / f"track_{gid}").glob("*.csv"))]
        row = {"id": t["id"], "laps_found": len(files)}
        if files:
            line, used = medoid_line([lap for lap in map(read_lap, files) if lap], args.max_laps)
            if line:
                f = Frame(t["lat"], t["lon"])
                pts = [f.xy(*p) for p in line]
                lap_m = length(pts)
                far = max(math.dist((0, 0), p) for p in pts)
                # the catalogue length is km or miles; the origin must be near the line
                ok_len = any(abs(lap_m - t["length"] * u) <= 0.06 * t["length"] * u for u in (1000, 1609.344))
                row.update(laps_used=used, lap_m=round(lap_m), origin_far_m=round(far), length_ok=ok_len)
                if far < 15_000:  # the catalogue length is only a hint (configs often carry the full-course value)
                    (out / f"{t['id']}.line.json").write_text(json.dumps(
                        {"track_id": t["id"], "source": "garage61", "laps": used, "step_m": STEP_M, "line": line},
                        separators=(",", ":")))
                    row["written"] = True
        report.append(row)
    json.dump(report, sys.stdout, indent=0)
    print(f"\n{sum(1 for r in report if r.get('written'))} of {len(report)} lines written", file=sys.stderr)


# ---------------------------------------------------------------- OSM classification

def is_pit(t) -> bool:
    return (t.get("raceway") in ("pitlane", "pit_lane") or t.get("service") in ("pit", "pit_lane")
            or bool(PIT_NAME.match(t.get("name", ""))))


def bg_kind(t, node: bool) -> str:
    if node:
        if t.get("natural") == "tree":
            return "tree"
        if t.get("power") in ("tower", "pole"):
            return "power_tower"
        return ""
    s = lambda k: t.get(k, "no") != "no"
    if s("bridge"):
        return "bridge"
    if t.get("power") in ("line", "minor_line"):
        return "power_line"
    if t.get("barrier") == "kerb":
        return "kerb"
    if s("barrier"):
        return "barrier"
    if t.get("building") == "grandstand":
        return "grandstand"
    if s("building"):
        return "building"
    if t.get("amenity") == "parking":
        return "parking"
    if t.get("natural") == "tree_row":
        return "tree_row"
    if t.get("landuse") == "forest" or t.get("natural") == "wood":
        return "area:forest"
    if t.get("landuse") in ("grass", "meadow") or t.get("natural") == "grassland":
        return "area:grass"
    if t.get("natural") == "scrub":
        return "area:scrub"
    if t.get("natural") == "water" or t.get("landuse") in ("reservoir", "basin"):
        return "area:water"
    if t.get("landuse") == "farmland":
        return "area:farmland"
    return ""


def simplify(pts, tol: float):
    """Douglas-Peucker in metres (iterative)."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = pts[i], pts[j]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        far, far_d = -1, tol
        for k in range(i + 1, j):
            px, py = pts[k]
            t = min(max(((px - ax) * dx + (py - ay) * dy) / l2, 0), 1) if l2 else 0
            d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > far_d:
                far, far_d = k, d
        if far >= 0:
            keep[far] = True
            stack += [(i, far), (far, j)]
    return [p for p, k in zip(pts, keep) if k]


# ---------------------------------------------------------------- build

def build_track(line_ll, elements, origin):
    """Returns (circuit, background) dicts in iRacing's frame for one track."""
    frame = Frame(*origin)
    line = [frame.xy(*p) for p in line_ll]
    if math.dist(line[0], line[-1]) > STEP_M:
        line.append(line[0])
    line = resample(line, STEP_M)
    lt = tangents(line)

    ways = []  # (id, tags, pts)
    nodes = []
    for e in elements:
        t = e.get("tags") or {}
        if e.get("type") == "node":
            nodes.append((e["id"], t, frame.xy(e["lat"], e["lon"])))
        elif e.get("type") == "way" and len(e.get("geometry") or []) > 1:
            ways.append((e["id"], t, [frame.xy(g["lat"], g["lon"]) for g in e["geometry"] if g]))

    # 1. fit iRacing line -> OSM on parallel roads
    fit_pts, fit_tan = [], []
    for _, t, pts in ways:
        if (t.get("highway") in FIT_ROADS or t.get("area:highway") == "raceway") and not is_pit(t):
            r = resample(pts, 3.0)
            fit_pts += r
            fit_tan += tangents(r)
    m = (1.0, 0.0, 0.0, 0.0)
    fitted = False
    if fit_pts:
        grid = Grid(fit_pts, 20.0)
        cos_fit = math.cos(math.radians(FIT_ANGLE))
        for thr in FIT_STEPS:
            src, dst = [], []
            for p, (tx, ty) in zip(line, lt):
                q = apply(m, p)
                rx, ry = m[0] * tx - m[1] * ty, m[1] * tx + m[0] * ty
                d, j = grid.near(q, thr, lambda j: abs(rx * fit_tan[j][0] + ry * fit_tan[j][1]) >= cos_fit)
                if j >= 0:
                    src.append(p)
                    dst.append(fit_pts[j])
            if len(src) < 0.3 * len(line):
                break
            prev, m, fitted = m, similarity(src, dst), True
            if thr == FIT_STEPS[-1] and max(math.dist(apply(prev, p), apply(m, p)) for p in line[:: max(1, len(line) // 50)]) < 0.05:
                break
    if not fitted:
        m = (1.0, 0.0, 0.0, 0.0)
    aligned = [apply(m, p) for p in line]
    at = tangents(aligned)
    inv = invert(m)

    # 2. select circuit runs: near, parallel, long enough
    lgrid = Grid(aligned, 20.0)
    cos_sel = math.cos(math.radians(MAX_ANGLE))

    def seg_dist(p):
        d, i = lgrid.near(p, KEEP_M + 25)
        if i < 0:
            return math.inf, -1
        best = d
        for j in (i - 1, i):
            if 0 <= j < len(aligned) - 1:
                (ax, ay), (bx, by) = aligned[j], aligned[j + 1]
                dx, dy = bx - ax, by - ay
                l2 = dx * dx + dy * dy or 1e-9
                u = min(max(((p[0] - ax) * dx + (p[1] - ay) * dy) / l2, 0), 1)
                best = min(best, math.hypot(p[0] - ax - u * dx, p[1] - ay - u * dy))
        return best, i

    runs, pit_ways = [], []
    for wid, t, pts in ways:
        if is_pit(t):
            pit_ways.append((wid, t, pts))
            continue
        if not (t.get("highway") in DRIVABLE or t.get("area:highway") == "raceway"):
            continue
        dense = resample(pts, 4.0) if length(pts) > 4 else pts
        wt = tangents(dense)
        cur = []
        for p, (tx, ty) in zip(dense + [None], wt + [(0.0, 0.0)]):
            ok = False
            if p is not None:
                d, i = seg_dist(p)
                ok = d <= KEEP_M and abs(tx * at[i][0] + ty * at[i][1]) >= cos_sel
            if ok:
                cur.append(p)
            else:
                if len(cur) > 1 and length(cur) >= MIN_RUN_M:
                    runs.append((wid, t, cur))
                cur = []

    # 3. stitch: for every line sample the nearest selected point, else the line itself
    sel = [p for _, _, r in runs for p in (resample(r, 2.0) if length(r) > 2 else r)]
    sgrid = Grid(sel, 10.0) if sel else None
    outline, offsets, from_osm = [], [], 0
    for p in aligned:
        d, j = sgrid.near(p, KEEP_M) if sgrid else (math.inf, -1)
        if j >= 0:
            outline.append(sel[j])
            offsets.append(d)
            from_osm += 1
        else:
            outline.append(p)
    # unaligned coverage, to show what the fit bought
    raw_cov = 0
    if sgrid:
        for p in line:
            raw_cov += sgrid.near(p, KEEP_M)[1] >= 0

    # 4. pit lane: pit-tagged ways that join this circuit and run alongside it
    def pit_of_this_layout(pts):
        d = [lgrid.near(q, 200.0)[0] for q in (resample(pts, 5.0) if length(pts) > 5 else pts)]
        return max(d[0], d[-1]) <= PIT_END_M and statistics.median(d) <= PIT_MEDIAN_M

    pits = [pts for _, _, pts in pit_ways if pit_of_this_layout(pts)]

    back = lambda pts: [frame.ll(apply(inv, p)) for p in pts]
    a, b, tx, ty = m
    cx = sum(p[0] for p in line) / len(line)
    cy = sum(p[1] for p in line) / len(line)
    moved = apply(m, (cx, cy))
    quality = {
        "aligned": fitted,
        "coverage": round(from_osm / len(aligned), 4),
        "coverage_unaligned": round(raw_cov / len(line), 4),
        "median_m": round(statistics.median(offsets), 2) if offsets else None,
        "p90_m": round(percentile(offsets, 90), 2) if offsets else None,
        "rotation_deg": round(math.degrees(math.atan2(b, a)), 4),
        "scale": round(math.hypot(a, b), 5),
        "shift_m": round(math.dist((cx, cy), moved), 2),
        "max_shift_m": round(max(math.dist(p, q) for p, q in zip(line, aligned)), 1),
        "lap_m": round(length(line)),
        "osm_ways": len({w for w, _, _ in runs}),
    }
    circuit = {"format": FORMAT, "frame": "iracing", "attribution": ATTRIBUTION, "license": LICENSE,
               "quality": quality, "outline": back(simplify(outline, 0.5)),
               "pit": [back(simplify(p, 0.5)) for p in pits]}

    # 5. background landmarks within BG_RADIUS_M of the line centre, capped per kind
    center = (cx, cy)
    by_kind = defaultdict(list)
    for wid, t, pts in ways:
        k = bg_kind(t, False)
        if not k:
            continue
        if (k.startswith("area:") or k in ("building", "grandstand", "parking")) and (len(pts) < 4 or pts[0] != pts[-1]):
            continue
        dist = math.dist(pts[0], moved)
        if dist <= BG_RADIUS_M:
            by_kind[k].append((dist, wid, simplify(pts, 1.0)))
    for nid, t, p in nodes:
        k = bg_kind(t, True)
        if k and math.dist(p, moved) <= BG_RADIUS_M:
            by_kind[k].append((math.dist(p, moved), nid, [p]))
    bg, points = [], 0
    for kind, cap in BG_KINDS:
        for dist, wid, pts in sorted(by_kind[kind])[:cap]:
            if points + len(pts) > BG_MAX_POINTS:
                continue
            points += len(pts)
            bg.append({"id": wid, "kind": kind, "geometry": back(pts)})
    background = {"format": FORMAT, "frame": "iracing", "attribution": ATTRIBUTION, "license": LICENSE, "ways": bg}
    return circuit, background


def cmd_build(args):
    catalogue = {t["id"]: t for t in json.loads(Path(args.catalogue).read_text())}
    lines, osm, out = Path(args.lines), Path(args.osm), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for lf in sorted(lines.glob("*.line.json"), key=lambda p: int(p.name.split(".")[0])):
        tid = int(lf.name.split(".")[0])
        parts = sorted(osm.glob(f"{tid}.*osm.json"))
        if args.ids and str(tid) not in args.ids.split(",") or not parts or tid not in catalogue:
            continue
        elements, seen, stamps = [], set(), []
        for part in parts:  # one file per Geofabrik region; a track on a border has two
            doc = json.loads(part.read_text())
            stamps.append(doc.get("osm_timestamp") or "")
            for e in doc["elements"]:
                if (e["type"], e["id"]) not in seen:
                    seen.add((e["type"], e["id"]))
                    elements.append(e)
        line = json.loads(lf.read_text())
        t = catalogue[tid]
        circuit, background = build_track(line["line"], elements, (t["lat"], t["lon"]))
        meta = {"track_id": tid, "built_at": built, "line_source": line["source"], "line_laps": line["laps"],
                "osm_timestamp": min(stamps)}
        (out / f"{tid}.circuit.json").write_text(json.dumps({**meta, **circuit}, separators=(",", ":"), ensure_ascii=False))
        (out / f"{tid}.background.json").write_text(json.dumps({**meta, **background}, separators=(",", ":"), ensure_ascii=False))
        rows.append({"track_id": tid, **circuit["quality"]})
        q = circuit["quality"]
        print(f"{tid:4d} cov {q['coverage']:.3f} (raw {q['coverage_unaligned']:.3f}) median {q['median_m']} p90 {q['p90_m']} "
              f"rot {q['rotation_deg']} shift {q['shift_m']} max {q['max_shift_m']}", file=sys.stderr)
    (out / "quality.json").write_text(json.dumps(rows, indent=1))


NOTICE = """Track outlines for the TeamManager telemetry map.

Map data (c) OpenStreetMap contributors, available under the Open Database License 1.0
(https://opendatacommons.org/licenses/odbl/1-0/, https://www.openstreetmap.org/copyright).
These files are a derived database of that data and are offered under the same licence.

Reference lines are derived from Garage 61 lap telemetry (line_source "garage61") or from
TeamManager users' own .ibt imports (line_source "ibt"); only a 5 m resampled line was used,
no driver names, lap ids or raw rows. Coordinates are in iRacing's own Lat/Lon frame.
"""


def cmd_bundle(args):
    """One zip per version (circuit/<id>.json, background/<id>.json, quality.json, NOTICE.txt), SHA256SUMS and
    provenance.json. The zip is byte-reproducible: fixed member order and timestamps."""
    built, out = Path(args.built), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = f"track-outlines-{args.version}.zip"
    tracks, sources, regions, built_at = [], defaultdict(int), set(), ""
    members, content, skipped = [], hashlib.sha256(), []
    for f in sorted(built.glob("*.circuit.json"), key=lambda p: int(p.name.split(".")[0])):
        tid = int(f.name.split(".")[0])
        circuit = json.loads(f.read_text())
        if circuit["quality"]["coverage"] < args.min_coverage:  # mostly the line itself: let the Server's fallback draw it
            skipped.append(tid)
            continue
        tracks.append(tid)
        sources[circuit["line_source"]] += 1
        regions.add(circuit.get("osm_timestamp") or "")
        built_at = max(built_at, circuit["built_at"])
        bg = (built / f"{tid}.background.json").read_bytes()
        members += [(f"circuit/{tid}.json", f.read_bytes()), (f"background/{tid}.json", bg)]
        for doc in (circuit, json.loads(bg)):  # geometry only: a new OSM snapshot without changes is no new release
            content.update(json.dumps({k: v for k, v in doc.items() if k not in ("built_at", "osm_timestamp")}, sort_keys=True).encode())
    members += [("quality.json", (built / "quality.json").read_bytes()), ("NOTICE.txt", NOTICE.encode())]
    with ZipFile(out / name, "w", ZIP_DEFLATED) as z:
        for arc, data in members:
            info = ZipInfo(arc, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, data)
    digest = hashlib.sha256((out / name).read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  {name}\n")
    (out / "provenance.json").write_text(json.dumps({
        "asset": name, "sha256": digest, "content_sha256": content.hexdigest(), "size": (out / name).stat().st_size, "format": FORMAT,
        "built_at": built_at, "builder_commit": args.commit, "tracks": tracks,
        "skipped_low_coverage": skipped, "min_coverage": args.min_coverage,
        "line_sources": dict(sorted(sources.items())),
        "osm": {"source": "Geofabrik regional extracts", "timestamps": sorted(regions - {""}),
                "attribution": ATTRIBUTION, "license": LICENSE},
    }, indent=1) + "\n")
    print(f"{name} {digest} {len(tracks)} tracks", file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("lines")
    a.add_argument("--g61", required=True, help="Garage 61 data root (telemetry/, telemetry-pro/, telemetry-pairs/)")
    a.add_argument("--catalogue", required=True, help="JSON list of {id,name,config,lat,lon,length}")
    a.add_argument("--out", required=True)
    a.add_argument("--ids", default="")
    a.add_argument("--max-laps", type=int, default=12)
    a.set_defaults(fn=cmd_lines)
    b = sub.add_parser("build")
    b.add_argument("--catalogue", required=True)
    b.add_argument("--lines", required=True)
    b.add_argument("--osm", required=True, help="directory of <id>.<region>.osm.json (Overpass `out geom` shape)")
    b.add_argument("--out", required=True)
    b.add_argument("--ids", default="")
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("bundle")
    c.add_argument("--built", required=True, help="output directory of build")
    c.add_argument("--version", required=True)
    c.add_argument("--commit", required=True, help="builder git commit")
    c.add_argument("--out", required=True)
    c.add_argument("--min-coverage", type=float, default=0.9, help="leave out tracks whose outline is mostly not OSM")
    c.set_defaults(fn=cmd_bundle)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
