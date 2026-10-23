#!/usr/bin/env python3
"""Helpers for the incremental outline release (.forgejo/workflows/track-outlines.yml).

  new-ids   --provenance <last release provenance.json> --catalogue catalogue.json --lines lines/
            prints the comma-separated catalogue track ids that have a reference line but are not in the release
  unpack    --zip <last release zip> --out out/      the release's circuit/background files and quality.json, as
            track_outlines.py build writes them (<id>.circuit.json, <id>.background.json)
  merge     --new new/ --out out/                    copies a build of some tracks over out/, quality.json keeping
            one row per track
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


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
            kind, _, base = name.partition("/")
            if kind in ("circuit", "background") and base.endswith(".json"):
                (out / f"{base[:-5]}.{kind}.json").write_bytes(z.read(name))
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
    args = p.parse_args(argv)
    if args.cmd == "new-ids":
        print(",".join(map(str, new_ids(Path(args.provenance), Path(args.catalogue), Path(args.lines)))))
    elif args.cmd == "unpack":
        unpack(Path(args.zip), Path(args.out))
    else:
        merge(Path(args.new), Path(args.out))


if __name__ == "__main__":
    main()
