#!/usr/bin/env python3
"""iRacing's own turn numbers for the built circuit outlines.

  fetch   catalogue (with each track's `track_map` folder and `layers` file names) -> <id>.active.svg and
          <id>.turns.svg from iRacing's public track-map CDN, one track after another, existing files kept
  place   built <id>.circuit.json + its reference line + the two SVGs -> adds `turns: [{number, label, apex_pct}]`
          (apex_pct = where the label sits along the reference lap from the start/finish line, 0..1, like LapDistPct) and
          `turns_fit` (fit error and transform) to the circuit file

The active layer is fitted onto the reference line (same frame as the laps) with a coarse rotation search and
then iterative closest point with a similarity (as the Web map does); each turn label goes through that fit
and snaps to the nearest line sample. A fit with a two-sided mean error over TURNS_MAX_ERROR_M places no turns.
`place` needs svgelements (`pip install svgelements`) to sample SVG paths; the rest is the standard library.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

from track_outlines import Frame, Grid, length, resample

USER_AGENT = "TeamManager-track-outlines/1 (circuit outline builder)"
TURNS_MAX_ERROR_M = 30.0  # the Web map's gate for printing turn numbers from the same fit
SCALE_SPAN = 0.25          # the scale stays within 25 % of the size estimate (Web fitSimilarity)
MAX_LABEL = 4              # "12", "3a", "T14": longer texts are not turn labels
MAX_SVG_BYTES = 2_000_000


# ---------------------------------------------------------------- fetch

def cmd_fetch(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = set(map(int, args.ids.split(","))) if args.ids else None
    for t in sorted(json.loads(Path(args.catalogue).read_text()), key=lambda t: t["id"]):
        layers = t.get("layers") or {}
        if wanted and t["id"] not in wanted or not t.get("track_map") or not {"active", "turns"} <= set(layers):
            continue
        for kind in ("active", "turns"):
            dest = out / f"{t['id']}.{kind}.svg"
            if dest.exists():
                continue
            url = t["track_map"].rstrip("/") + "/" + layers[kind]
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=60) as r:
                    body = r.read(MAX_SVG_BYTES + 1)
            except OSError as e:
                print(f"{t['id']} {kind}: {e}", file=sys.stderr)
                continue
            if len(body) <= MAX_SVG_BYTES:
                dest.write_bytes(body)
            time.sleep(args.pause)


# ---------------------------------------------------------------- fit

def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def umeyama(src, dst, limit):
    """Least-squares similarity src[i] -> dst[i] as (a, b, tx, ty), scale clamped to `limit`."""
    (mx, my), (nx, ny) = centroid(src), centroid(dst)
    dot = cross = norm = 0.0
    for (x, y), (u, v) in zip(src, dst):
        px, py, qx, qy = x - mx, y - my, u - nx, v - ny
        dot += px * qx + py * qy
        cross += px * qy - py * qx
        norm += px * px + py * py
    a, b = dot / norm, cross / norm
    s = math.hypot(a, b) or 1.0
    c = min(max(s, limit[0]), limit[1]) / s
    a, b = a * c, b * c
    return a, b, nx - (a * mx - b * my), ny - (b * mx + a * my)


def move(m, p):
    a, b, tx, ty = m
    return a * p[0] - b * p[1] + tx, b * p[0] + a * p[1] + ty


def decimate(pts, n):
    step = max(1, len(pts) // n)
    return pts[::step]


def nearest(grid, pts, p):
    """Nearest of `pts` to p: the grid answers within 200 m, else every point is compared."""
    i = grid.near(p, 200.0)[1]
    return pts[i] if i >= 0 else min(pts, key=lambda q: math.dist(p, q))


def fit_svg(src, dst):
    """Fit SVG points (y already pointing north) onto line points in metres: (transform, two-sided mean error)."""
    dgrid = Grid(dst, 25.0)

    def error(m):
        moved = [move(m, p) for p in src]
        mgrid = Grid(moved, 25.0)
        one = sum(math.dist(q, nearest(dgrid, dst, q)) for q in moved) / len(moved)
        other = sum(math.dist(p, nearest(mgrid, moved, p)) for p in dst) / len(dst)
        return max(one, other)

    (sx, sy), (dx, dy) = centroid(src), centroid(dst)
    radius = lambda pts, c: math.sqrt(sum(math.dist(p, c) ** 2 for p in pts) / len(pts))
    scale = radius(dst, (dx, dy)) / radius(src, (sx, sy))
    limit = (scale * (1 - SCALE_SPAN), scale * (1 + SCALE_SPAN))
    starts = []
    for step in range(24):
        a, b = scale * math.cos(step * math.pi / 12), scale * math.sin(step * math.pi / 12)
        m = (a, b, dx - (a * sx - b * sy), dy - (b * sx + a * sy))
        starts.append((error(m), m))
    best = None
    for _, m in sorted(starts)[:2]:
        for _ in range(15):
            m = umeyama(src, [nearest(dgrid, dst, move(m, p)) for p in src], limit)
        e = error(m)
        if best is None or e < best[0]:
            best = (e, m)
    return best[1], best[0]


def place_turns(labels, m, line):
    """Each (label, x, y) through the fit onto the nearest line sample: [{number, label, apex_pct}] in lap order."""
    cum = [0.0]
    for p, q in zip(line, line[1:]):
        cum.append(cum[-1] + math.dist(p, q))
    total = cum[-1] or 1.0
    grid = Grid(line, 25.0)
    out = []
    for label, x, y in labels:
        p = move(m, (x, y))
        d, i = grid.near(p, 500.0)
        if i < 0:
            continue
        number = re.match(r"\D*(\d+)", label)
        if number:  # a word label ("Big", "Bend") names a place, not a turn
            out.append({"number": int(number.group(1)), "label": label, "apex_pct": round(cum[i] / total, 5)})
    return sorted(out, key=lambda t: t["apex_pct"])


# ---------------------------------------------------------------- SVG reading (svgelements)

def svg_points(path: Path, step_px: float = 6.0):
    import svgelements  # only `place` needs it

    pts = []
    for e in svgelements.SVG.parse(str(path)).elements():
        if isinstance(e, svgelements.Shape) and not isinstance(e, svgelements.Path):
            e = svgelements.Path(e)
        if isinstance(e, svgelements.Path):
            for seg in e.segments():
                if isinstance(seg, svgelements.Move):
                    continue
                a, b = seg.start, seg.end
                n = max(1, int(abs(b - a) / step_px)) if a is not None and b is not None else 1
                pts += [(p.x, -p.y) for p in (seg.point(k / n) for k in range(n + 1)) if p is not None]
    return pts


def svg_labels(path: Path):
    import svgelements

    out = []
    for e in svgelements.SVG.parse(str(path)).elements():
        if isinstance(e, svgelements.Text):
            label = (e.text or "").strip()
            if 0 < len(label) <= MAX_LABEL and e.x is not None:
                p = e.transform.point_in_matrix_space((e.x, e.y)) if e.transform else svgelements.Point(e.x, e.y)
                out.append((label, p.x, -p.y))
    return out[:80]


def cmd_place(args):
    built, lines, svg = Path(args.built), Path(args.lines), Path(args.svg)
    rows = []
    for cf in sorted(built.glob("*.circuit.json"), key=lambda p: int(p.name.split(".")[0])):
        tid = int(cf.name.split(".")[0])
        active, turns, lf = svg / f"{tid}.active.svg", svg / f"{tid}.turns.svg", lines / f"{tid}.line.json"
        if args.ids and str(tid) not in args.ids.split(",") or not (active.exists() and turns.exists() and lf.exists()):
            continue
        line_ll = json.loads(lf.read_text())["line"]
        frame = Frame(*line_ll[0])
        line = resample([frame.xy(*p) for p in line_ll], 5.0)
        src, labels = svg_points(active), svg_labels(turns)
        circuit = json.loads(cf.read_text())
        circuit.pop("turns", None)
        if len(src) > 10 and labels:
            m, error = fit_svg(decimate(src, 150), decimate(line, 250))
            circuit["turns_fit"] = {"error_m": round(error, 1), "scale_m_per_px": round(math.hypot(m[0], m[1]), 4),
                                    "rotation_deg": round(math.degrees(math.atan2(m[1], m[0])), 2)}
            if error <= TURNS_MAX_ERROR_M:
                circuit["turns"] = place_turns(labels, m, line)
        cf.write_text(json.dumps(circuit, separators=(",", ":"), ensure_ascii=False))
        fit = circuit.get("turns_fit", {})
        rows.append({"track_id": tid, "turns": len(circuit.get("turns", [])), "labels": len(labels), **fit})
        print(f"{tid:4d} turns {len(circuit.get('turns', []))}/{len(labels)} error {fit.get('error_m')} m", file=sys.stderr)
    (built / "turns-quality.json").write_text(json.dumps(rows, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("fetch")
    a.add_argument("--catalogue", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--ids", default="")
    a.add_argument("--pause", type=float, default=1.0)
    a.set_defaults(fn=cmd_fetch)
    b = sub.add_parser("place")
    b.add_argument("--built", required=True)
    b.add_argument("--lines", required=True)
    b.add_argument("--svg", required=True)
    b.add_argument("--ids", default="")
    b.set_defaults(fn=cmd_place)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
