#!/usr/bin/env python3
"""iRacing's own turn numbers for the built circuit outlines.

  fetch   catalogue (with each track's `track_map` folder and `layers` file names) -> <id>.active.svg and
          <id>.turns.svg from iRacing's public track-map CDN, one track after another; a file older than
          --max-age-days is asked for again with a conditional GET. fetched.json records url, sha256 and fetch time.
  place   built <id>.circuit.json + its reference line + the two SVGs -> adds `turns: [{number, label, apex_pct}]`
          (apex_pct = where the label sits along the reference lap from the start/finish line, 0..1, like LapDistPct),
          `turns_fit` (fit error, transform, lap-order inversions) and `turns_source` (the two SVGs) to the circuit file

The active layer is fitted onto the reference line (same frame as the laps) with a coarse rotation search and then
iterative closest point with a similarity (as the Web map does); each turn label goes through that fit and snaps to
the nearest line sample. Only labels like "3", "3a" or "T14" are turns. Neighbouring labels in the wrong order
within 200 m (chicanes) are put back in number order; a track whose labels still break the lap order more than
twice, or whose fit error is over TURNS_MAX_ERROR_M, gets no turns.
`place` needs svgelements (`pip install svgelements`) to sample SVG paths; the rest is the standard library.
"""
from __future__ import annotations

import argparse
import email.utils
import hashlib
import json
import math
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from track_outlines import Frame, Grid, apply as move, length, resample, similarity

USER_AGENT = "TeamManager-track-outlines/1 (circuit outline builder)"
TURNS_MAX_ERROR_M = 30.0  # the Web map's gate for printing turn numbers from the same fit
SCALE_SPAN = 0.25          # the scale stays within 25 % of the size estimate (Web fitSimilarity)
TURN_LABEL = re.compile(r"T?(\d{1,2})[a-z]?")  # "3", "3a", "T14"; not "100R", "180º", "TV3" or words
CLOSE_TURNS_M = 200.0      # labels this close may swap places (chicanes): put them back in number order
MAX_INVERSIONS = 2         # more breaks of the lap order than this after the fix: the fit or labels are wrong
MAX_SVG_BYTES = 2_000_000


# ---------------------------------------------------------------- fetch

def cmd_fetch(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    record_path = out / "fetched.json"
    record = json.loads(record_path.read_text()) if record_path.exists() else {}
    wanted = set(map(int, args.ids.split(","))) if args.ids else None
    for t in sorted(json.loads(Path(args.catalogue).read_text()), key=lambda t: t["id"]):
        layers = t.get("layers") or {}
        if wanted and t["id"] not in wanted or not t.get("track_map") or not {"active", "turns"} <= set(layers):
            continue
        for kind in ("active", "turns"):
            dest, key = out / f"{t['id']}.{kind}.svg", f"{t['id']}.{kind}"
            url = t["track_map"].rstrip("/") + "/" + layers[kind]
            seen = record.get(key, {})
            if dest.exists() and seen.get("url") == url and time.time() - seen.get("checked", 0) < args.max_age_days * 86400:
                continue
            headers = {"User-Agent": USER_AGENT}
            if dest.exists() and seen.get("url") == url and seen.get("last_modified"):
                headers["If-Modified-Since"] = seen["last_modified"]
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                    body, modified = r.read(MAX_SVG_BYTES + 1), r.headers.get("Last-Modified")
            except urllib.error.HTTPError as e:
                if e.code == 304:  # unchanged since the last fetch
                    record[key] = {**seen, "checked": time.time()}
                else:
                    print(f"{t['id']} {kind}: {e}", file=sys.stderr)
                continue
            except OSError as e:
                print(f"{t['id']} {kind}: {e}", file=sys.stderr)
                continue
            finally:
                time.sleep(args.pause)
            if len(body) <= MAX_SVG_BYTES:
                dest.write_bytes(body)
                record[key] = {"url": url, "sha256": hashlib.sha256(body).hexdigest(), "fetched_at": now,
                               "last_modified": modified or email.utils.formatdate(usegmt=True), "checked": time.time()}
    record_path.write_text(json.dumps(record, indent=1, sort_keys=True))


# ---------------------------------------------------------------- fit

def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


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
            m = similarity(src, [nearest(dgrid, dst, move(m, p)) for p in src], scale_range=limit)
        e = error(m)
        if best is None or e < best[0]:
            best = (e, m)
    return best[1], best[0]


def inversions(turns):
    """Breaks of the lap order: number decreases between neighbours, going round the lap once (the one wrap from the
    last turn to the first, where the start/finish line sits, is no break)."""
    n = [t["number"] for t in turns]
    return max(0, sum(1 for a, b in zip(n, n[1:] + n[:1]) if b < a) - 1) if len(n) > 1 else 0


def fix_close_order(turns, lap_m):
    """Labels within CLOSE_TURNS_M of each other keep their positions, but take their numbers in order."""
    out, i = [], 0
    while i < len(turns):
        j = i
        while j + 1 < len(turns) and (turns[j + 1]["apex_pct"] - turns[j]["apex_pct"]) * lap_m < CLOSE_TURNS_M:
            j += 1
        group = turns[i:j + 1]
        names = sorted(((t["number"], t["label"]) for t in group))
        out += [{"number": n, "label": label, "apex_pct": t["apex_pct"]} for (n, label), t in zip(names, group)]
        i = j + 1
    return out


def place_turns(labels, m, line):
    """Each (label, x, y) through the fit onto the nearest sample of the closed line: [{number, label, apex_pct}]."""
    if math.dist(line[0], line[-1]) > 1.0:
        line = line + [line[0]]
    cum = [0.0]
    for p, q in zip(line, line[1:]):
        cum.append(cum[-1] + math.dist(p, q))
    total = cum[-1] or 1.0
    grid = Grid(line, 25.0)
    out, seen = [], set()
    for label, x, y in labels:
        number = TURN_LABEL.fullmatch(label)
        d, i = grid.near(move(m, (x, y)), 500.0)
        if not number or i < 0:
            continue
        turn = {"number": int(number.group(1)), "label": label, "apex_pct": round(cum[i] / total % 1.0, 5)}
        if (label, turn["apex_pct"]) not in seen:
            seen.add((label, turn["apex_pct"]))
            out.append(turn)
    return sorted(out, key=lambda t: t["apex_pct"])


# ---------------------------------------------------------------- SVG reading

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


MATRIX = re.compile(r"matrix\(\s*" + r"[\s,]+".join([r"(-?[\d.]+)"] * 6) + r"\s*\)")
TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)(?:[\s,]+(-?[\d.]+))?\s*\)")


def svg_labels(path: Path):
    """(label, x, -y) per <text>: its tspans joined ("1"+"1" is "11"), placed by the text's own matrix(), translate()
    or x/y."""
    out = []
    for el in ET.parse(path).getroot().iter():
        if el.tag.rsplit("}", 1)[-1] != "text":
            continue
        label = "".join(el.itertext()).strip()
        transform = el.get("transform") or ""
        m, t = MATRIX.search(transform), TRANSLATE.search(transform)
        if m:
            x, y = float(m.group(5)), float(m.group(6))
        elif t:
            x, y = float(t.group(1)), float(t.group(2) or 0)
        elif el.get("x") is not None:
            x, y = float(el.get("x")), float(el.get("y", 0))
        else:
            continue
        if label:
            out.append((label, x, -y))
    return out[:80]


def place_track(tid, circuit, line_ll, active, turns_svg, record):
    """Adds turns, turns_fit and turns_source to one circuit (in place); returns the quality row."""
    frame = Frame(*line_ll[0])
    line = resample([frame.xy(*p) for p in line_ll], 5.0)
    src, labels = svg_points(active), svg_labels(turns_svg)
    circuit.pop("turns", None)
    circuit.pop("turns_fit", None)
    circuit["turns_source"] = {kind: {k: v for k, v in record.get(f"{tid}.{kind}", {}).items() if k in ("url", "sha256", "fetched_at")}
                               for kind in ("active", "turns")}
    row = {"track_id": tid, "labels": len(labels), "turns": 0}
    if len(src) > 10 and labels:
        m, error = fit_svg(decimate(src, 150), decimate(line, 250))
        raw = place_turns(labels, m, line)
        placed, before = fix_close_order(raw, length(line)), inversions(raw)
        circuit["turns_fit"] = {"error_m": round(error, 1), "scale_m_per_px": round(math.hypot(m[0], m[1]), 4),
                                "rotation_deg": round(math.degrees(math.atan2(m[1], m[0])), 2),
                                "inversions_before_fix": before, "inversions": inversions(placed)}
        if error <= TURNS_MAX_ERROR_M and inversions(placed) <= MAX_INVERSIONS:
            circuit["turns"] = placed
        row.update(turns=len(circuit.get("turns", [])), **circuit["turns_fit"])
    return row


def cmd_place(args):
    built, lines, svg = Path(args.built), Path(args.lines), Path(args.svg)
    record = json.loads((svg / "fetched.json").read_text()) if (svg / "fetched.json").exists() else {}
    rows = []
    for cf in sorted(built.glob("*.circuit.json"), key=lambda p: int(p.name.split(".")[0])):
        tid = int(cf.name.split(".")[0])
        active, turns_svg, lf = svg / f"{tid}.active.svg", svg / f"{tid}.turns.svg", lines / f"{tid}.line.json"
        if args.ids and str(tid) not in args.ids.split(",") or not (active.exists() and turns_svg.exists() and lf.exists()):
            continue
        circuit = json.loads(cf.read_text())
        try:
            row = place_track(tid, circuit, json.loads(lf.read_text())["line"], active, turns_svg, record)
        except Exception as e:  # one broken SVG must not stop the other tracks; that track keeps no turns
            for key in ("turns", "turns_fit", "turns_source"):
                circuit.pop(key, None)
            row = {"track_id": tid, "turns": 0, "error": f"{type(e).__name__}: {e}"[:200]}
        cf.write_text(json.dumps(circuit, separators=(",", ":"), ensure_ascii=False))
        rows.append(row)
        print(f"{tid:4d} turns {row['turns']}/{row.get('labels', 0)} error {row.get('error_m', row.get('error'))} "
              f"inversions {row.get('inversions')}", file=sys.stderr)
    (built / "turns-quality.json").write_text(json.dumps(rows, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("fetch")
    a.add_argument("--catalogue", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--ids", default="")
    a.add_argument("--pause", type=float, default=1.0)
    a.add_argument("--max-age-days", type=float, default=6.0, help="ask again (conditional GET) after this long")
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
