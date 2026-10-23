#!/usr/bin/env python3
"""Helpers for the incremental outline release (.forgejo/workflows/track-outlines.yml).

  new-ids   --provenance <last release provenance.json> --catalogue catalogue.json --lines lines/
            prints the comma-separated catalogue track ids that have a reference line but are not in the release
  unpack    --zip <last release zip> --out out/      the release's circuit/background files and quality.json, as
            track_outlines.py build writes them (<id>.circuit.json, <id>.background.json)
  merge     --new new/ --out out/                    copies a build of some tracks over out/, quality.json keeping
            one row per track
  keep-ids  --ids 1,2 --plan plan.json --catalogue catalogue.json --record skipped.json
            prints the ids that have a Geofabrik region (or are fictional, which need none); the others are
            recorded once in --record and left out
  full      --provenance <last release provenance.json>   exit 0 when a full rebuild is needed (another format)
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

from track_outlines import FICTIONAL, FORMAT

MEMBER = re.compile(r"(circuit|background)/(\d{1,6})\.json")  # nothing else of a release zip is unpacked


def new_ids(provenance: Path, catalogue: Path, lines: Path) -> list[int]:
    released = set(json.loads(provenance.read_text())["tracks"])
    known = {t["id"] for t in json.loads(catalogue.read_text())}
    have_line = {int(p.name.split(".")[0]) for p in lines.glob("*.line.json")}
    return sorted((known & have_line) - released)


def unpack(release: Path, out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(release) as z:
        for name in z.namelist():
            if m := MEMBER.fullmatch(name):
                kind, tid = m.group(1), int(m.group(2))
                (out / f"{tid}.{kind}.json").write_bytes(z.read(name))
                n += kind == "circuit"
        (out / "quality.json").write_bytes(z.read("quality.json"))
    return n


def merge(new: Path, out: Path) -> None:
    rows = {r["track_id"]: r for r in json.loads((out / "quality.json").read_text())} if (out / "quality.json").exists() else {}
    if (new / "quality.json").exists():
        rows.update({r["track_id"]: r for r in json.loads((new / "quality.json").read_text())})
    for p in new.glob("*.*.json"):
        shutil.copy(p, out / p.name)
    (out / "quality.json").write_text(json.dumps([rows[k] for k in sorted(rows)], indent=1))


def keep_ids(ids: list[int], plan: Path, catalogue: Path, record: Path) -> list[int]:
    areas = json.loads(plan.read_text())["areas"]
    names = {t["id"]: t["name"] for t in json.loads(catalogue.read_text())}
    keep = [i for i in ids if str(i) in areas or FICTIONAL.match(names.get(i, ""))]
    skipped = json.loads(record.read_text()) if record.exists() else {}
    for i in ids:
        if i not in keep and str(i) not in skipped:
            skipped[str(i)] = names.get(i, "")
            print(f"track {i} ({names.get(i, '')}): no Geofabrik region, left out", file=sys.stderr)
    record.write_text(json.dumps(skipped, indent=1, sort_keys=True))
    return keep


def needs_full(provenance: Path) -> bool:
    return json.loads(provenance.read_text()).get("format") != FORMAT


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new-ids")
    a.add_argument("--provenance", required=True)
    a.add_argument("--catalogue", required=True)
    a.add_argument("--lines", required=True)
    b = sub.add_parser("unpack")
    b.add_argument("--zip", required=True)
    b.add_argument("--out", required=True)
    c = sub.add_parser("merge")
    c.add_argument("--new", required=True)
    c.add_argument("--out", required=True)
    d = sub.add_parser("keep-ids")
    d.add_argument("--ids", required=True)
    d.add_argument("--plan", required=True)
    d.add_argument("--catalogue", required=True)
    d.add_argument("--record", required=True)
    e = sub.add_parser("full")
    e.add_argument("--provenance", required=True)
    args = p.parse_args(argv)
    if args.cmd == "new-ids":
        print(",".join(map(str, new_ids(Path(args.provenance), Path(args.catalogue), Path(args.lines)))))
    elif args.cmd == "unpack":
        unpack(Path(args.zip), Path(args.out))
    elif args.cmd == "merge":
        merge(Path(args.new), Path(args.out))
    elif args.cmd == "keep-ids":
        print(",".join(map(str, keep_ids([int(i) for i in args.ids.split(",") if i], Path(args.plan), Path(args.catalogue), Path(args.record)))))
    else:
        sys.exit(0 if needs_full(Path(args.provenance)) else 1)


if __name__ == "__main__":
    main()
