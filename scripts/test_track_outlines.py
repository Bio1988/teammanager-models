import contextlib
import io
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

import track_outlines as T

ORIGIN = (47.95, 0.21)
FRAME = T.Frame(*ORIGIN)


def ll(points):
    return [FRAME.ll(p) for p in points]


def stadium(scale=1.0):
    """A 2.4 km rounded-rectangle lap in metres, counter-clockwise."""
    pts = []
    for i in range(0, 800, 5):
        pts.append((i * scale, 0.0))
    for k in range(0, 180, 3):
        a = math.radians(k - 90)
        pts.append((800 * scale + 200 * math.cos(a), 200 + 200 * math.sin(a)))
    for i in range(800, 0, -5):
        pts.append((i * scale, 400.0))
    for k in range(0, 180, 3):
        a = math.radians(k + 90)
        pts.append((200 * math.cos(a), 200 + 200 * math.sin(a)))
    return pts


def way(wid, tags, points):
    return {"type": "way", "id": wid, "tags": tags, "geometry": [{"lat": a, "lon": b} for a, b in ll(points)]}


class BuildTrackTest(unittest.TestCase):
    def setUp(self, degrees=0.5):
        # OSM is the lap rotated by 0.5 deg about (400, 200) and shifted 25 m east and north: iRacing's frame is off
        r = math.radians(degrees)
        move = lambda p: (400 + (p[0] - 400) * math.cos(r) - (p[1] - 200) * math.sin(r) + 25,
                          225 + (p[0] - 400) * math.sin(r) + (p[1] - 200) * math.cos(r))
        lap = stadium()
        osm_lap = [move(p) for p in lap]
        half = len(osm_lap) // 2
        self.elements = [
            way(1, {"highway": "raceway"}, osm_lap[: half + 1]),
            way(2, {"highway": "primary"}, osm_lap[half:] + osm_lap[:1]),  # public road part of the lap
            way(3, {"highway": "raceway", "name": "Karting"}, [(300, 120), (500, 120), (500, 280), (300, 280), (300, 120)]),
            way(4, {"highway": "tertiary"}, [(600, -300), (600, 700)]),  # crosses the lap at right angles
            way(5, {"highway": "raceway", "name": "Pit Lane"}, [move((200, 25)), move((600, 25))]),
            way(8, {"service": "pit_lane"}, [move((300, 150)), move((500, 150))]),  # another layout's pit lane, inside the lap
            way(6, {"landuse": "forest"}, [(900, 600), (1000, 600), (1000, 700), (900, 600)]),
            {"type": "node", "id": 7, "lat": ll([(100, 600)])[0][0], "lon": ll([(100, 600)])[0][1], "tags": {"natural": "tree"}},
        ]
        self.line = ll(lap)

    def test_aligns_selects_and_stitches(self):
        circuit, background = T.build_track(self.line, self.elements, ORIGIN)
        q = circuit["quality"]
        self.assertTrue(q["aligned"])
        self.assertGreater(q["coverage"], 0.97)
        self.assertLess(q["coverage_unaligned"], 0.5)
        self.assertAlmostEqual(q["rotation_deg"], 0.5, delta=0.05)
        self.assertLess(q["p90_m"], 1.0)
        # outline is in iRacing's frame: back on the lap, and never on the karting loop inside it
        outline = [FRAME.xy(*p) for p in circuit["outline"]]
        lap = T.Grid(T.resample(stadium(), 1.0), 10.0)
        self.assertLess(max(lap.near(p, 50)[0] for p in outline), 2.0)
        self.assertEqual(len(circuit["pit"]), 1)
        kinds = sorted(w["kind"] for w in background["ways"])
        self.assertEqual(kinds, ["area:forest", "tree"])
        self.assertEqual(circuit["attribution"], T.ATTRIBUTION)

    def test_street_circuit_uses_every_drivable_way_kind(self):
        lap = stadium()
        n = len(lap) // 4
        parts = [({"highway": "raceway"}, lap[: n + 1]), ({"aeroway": "taxiway"}, lap[n: 2 * n + 1]),
                 ({"disused:highway": "raceway", "name": "Grand Prix"}, lap[2 * n: 3 * n + 1]),
                 ({"highway": "pedestrian"}, lap[3 * n:] + lap[:1])]
        elements = [way(i, t, pts) for i, (t, pts) in enumerate(parts, 1)]
        circuit, _ = T.build_track(ll(lap), elements, ORIGIN)
        self.assertGreater(circuit["quality"]["coverage"], 0.97)
        self.assertEqual(circuit["quality"]["osm_ways"], 4)
        # a footway is not drivable
        elements[3]["tags"] = {"highway": "footway"}
        self.assertLess(T.build_track(ll(lap), elements, ORIGIN)[0]["quality"]["coverage"], 0.8)

    def test_frame_hundreds_of_metres_off_is_found(self):
        lap = stadium()
        elements = [way(1, {"highway": "raceway", "surface": "dirt"}, [(x + 300, y - 150) for x, y in lap + lap[:1]])]
        circuit, _ = T.build_track(ll(lap), elements, ORIGIN)
        self.assertTrue(circuit["quality"]["aligned"])
        self.assertGreater(circuit["quality"]["coverage"], 0.97)

    def test_a_decoy_road_far_away_is_not_followed(self):
        lap = stadium()
        decoy = [way(1, {"highway": "raceway"}, [(x + 300, 600) for x in range(0, 800, 20)])]  # straight, a third of the lap
        circuit, _ = T.build_track(ll(lap), decoy, ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["coverage"], 0)

    def test_an_implausible_fit_is_dropped(self):
        self.setUp(degrees=3.0)  # beyond any measured iRacing offset: these would be the wrong roads
        circuit, _ = T.build_track(self.line, self.elements, ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["rotation_deg"], 0)

    def test_the_line_fills_where_osm_has_no_way_and_says_where(self):
        half = [e for e in self.elements if e["id"] != 2]  # the public-road half of the lap is missing
        circuit, _ = T.build_track(self.line, half, ORIGIN, width_m=9.0)
        q = circuit["quality"]
        self.assertEqual({k for _, _, k in q["sources"]}, {"osm", "line"})
        self.assertEqual(q["sources"][0][0], 0.0)
        self.assertEqual(q["label"], "mixed" if q["coverage"] >= 0.5 else "line")
        self.assertEqual(circuit["width_m"], 9.0)
        outline = [FRAME.xy(*p) for p in circuit["outline"]]
        self.assertGreater(T.length(outline), 0.95 * q["lap_m"])  # the whole lap, OSM part and line part

    def test_a_circuit_on_residential_roads_is_still_aligned(self):
        residential = [{**e, "tags": {"highway": "residential"}} if e["id"] in (1, 2) else e for e in self.elements]
        self.assertTrue(T.build_track(self.line, residential, ORIGIN)[0]["quality"]["aligned"])

    def test_only_the_iracing_superspeedway_is_fictional(self):
        self.assertTrue(T.FICTIONAL.match("iRacing Superspeedway"))
        self.assertFalse(T.FICTIONAL.match("Daytona International Speedway"))

    def test_without_roads_keeps_the_line_and_says_so(self):
        circuit, _ = T.build_track(self.line, [], ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["coverage"], 0)
        self.assertGreater(len(circuit["outline"]), 10)


class BundleTest(unittest.TestCase):
    def built(self, coverages):
        built = Path(self.enterContext(tempfile.TemporaryDirectory()))
        circuit, background = T.build_track(ll(stadium()), [], ORIGIN)
        for tid, (coverage, label) in coverages.items():
            circuit["quality"].update(coverage=coverage, label=label)
            meta = {"track_id": tid, "built_at": "2026-10-22T00:00:00Z", "line_source": "garage61", "line_laps": 3, "osm_timestamp": "2026-10-21T20:00:00Z"}
            (built / f"{tid}.circuit.json").write_text(json.dumps({**meta, **circuit}))
            (built / f"{tid}.background.json").write_text(json.dumps({**meta, **background}))
        (built / "quality.json").write_text("[]")
        (built / "catalogue.json").write_text(json.dumps([{"id": i, "name": f"Track {i}", "config": ""} for i in (7, 8, 9)]))
        return built

    def bundle(self, built, version="t1"):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        T.cmd_bundle(SimpleNamespace(built=str(built), version=version, commit="abc", out=str(out), catalogue=str(built / "catalogue.json")))
        return out

    def test_bundle_is_reproducible_and_carries_provenance(self):
        built = self.built({7: (0.95, "osm")})
        first, second = self.bundle(built), self.bundle(built)
        self.assertEqual((first / "SHA256SUMS").read_text(), (second / "SHA256SUMS").read_text())
        provenance = json.loads((second / "provenance.json").read_text())
        self.assertEqual(provenance["tracks"], [7])
        self.assertEqual(provenance["line_sources"], {"garage61": 1})
        self.assertIn(provenance["sha256"], (second / "SHA256SUMS").read_text())
        with zipfile.ZipFile(second / "track-outlines-t1.zip") as z:
            self.assertEqual(z.namelist(), ["circuit/7.json", "background/7.json", "quality.json", "NOTICE.txt"])
            self.assertIn(b"OpenStreetMap contributors", z.read("NOTICE.txt"))

    def test_every_track_with_a_line_ships_and_the_rest_needs_a_line(self):
        out = self.bundle(self.built({7: (0.95, "osm"), 8: (0.2, "line")}))
        provenance = json.loads((out / "provenance.json").read_text())
        self.assertEqual((provenance["tracks"], provenance["labels"]), ([7, 8], {"line": 1, "osm": 1}))
        self.assertEqual([(n["track_id"], n["reason"][:10]) for n in json.loads((out / "needs-line.json").read_text())],
                         [(8, "OSM covers"), (9, "no referen")])

    def test_an_empty_bundle_fails(self):
        empty = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (empty / "catalogue.json").write_text("[]")
        with self.assertRaises(SystemExit):
            self.bundle(empty)


class LinesTest(unittest.TestCase):
    def g61(self, tracks):
        """A G61 root: {g61 id: (track, variant, number of laps)} under telemetry-pairs/, named by _missing_laps.csv."""
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "telemetry").mkdir()
        index = "track_id,track,variant\n"
        for gid, (track, variant, laps) in tracks.items():
            index += f"{gid},{track},{variant}\n"
            (root / "telemetry-pairs" / f"track_{gid}").mkdir(parents=True)
            for k in range(laps):
                rows = "".join(f"{i},0,0,0,{a},{b}\n" for i, (a, b) in enumerate(ll([(x, y + k) for x, y in stadium()])))
                (root / "telemetry-pairs" / f"track_{gid}" / f"lap{gid}-{k}.csv").write_text(
                    "sample,t_s,Speed,LapDistPct,Lat,Lon\n#,60 Hz,m/s,0-1,deg,deg\n" + rows)
        (root / "telemetry" / "_missing_laps.csv").write_text(index)
        return root

    def lines(self, root, catalogue, out=None):
        miles = T.length(stadium()) / 1609.344
        (root / "catalogue.json").write_text(json.dumps([{"lat": ORIGIN[0], "lon": ORIGIN[1], "length": miles, **t} for t in catalogue]))
        out = out or root / "lines"
        with contextlib.redirect_stdout(io.StringIO()):
            T.cmd_lines(SimpleNamespace(g61=str(root), catalogue=str(root / "catalogue.json"), out=str(out), ids="", max_laps=12))
        return sorted(int(p.name.split(".")[0]) for p in out.glob("*.line.json"))

    def test_retired_layouts_match_loosely_only_with_the_catalogue_length(self):
        root = self.g61({5: ("Phoenix Raceway - 2008", "Rallycross", 2)})
        legacy = {"id": 306, "name": "[Legacy] Phoenix Raceway - 2008", "config": "Rallycross"}
        self.assertEqual(self.lines(root, [legacy]), [306])
        self.assertEqual(self.lines(root, [{**legacy, "length": 9.0}], root / "other"), [])

    def test_a_retired_layout_never_borrows_the_current_layouts_laps(self):
        root = self.g61({7: ("Charlotte Motor Speedway", "Roval", 3)})
        current = {"id": 340, "name": "Charlotte Motor Speedway", "config": "Roval"}
        retired = {"id": 341, "name": "[Retired] Charlotte Motor Speedway", "config": "[Retired] Roval"}
        self.assertEqual(self.lines(root, [current, retired]), [340])

    def test_one_lap_is_no_loose_line_and_an_own_import_line_wins(self):
        root = self.g61({8: ("Lanier National Speedway", "Dirt", 1), 9: ("Road America", "Full Course", 2)})
        out = root / "lines"
        out.mkdir()
        (out / "18.line.json").write_text(json.dumps({"track_id": 18, "source": "ibt", "laps": 12, "line": []}))
        found = self.lines(root, [{"id": 288, "name": "[Legacy] Lanier National Speedway", "config": "Dirt"},
                                  {"id": 18, "name": "Road America", "config": "Full Course"}], out)
        self.assertEqual(found, [18])
        self.assertEqual(json.loads((out / "18.line.json").read_text())["source"], "ibt")

    def test_a_lap_file_without_coordinates_is_empty(self):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (d / "empty.csv").write_text("")
        (d / "nogps.csv").write_text("sample,Speed\n#,m/s\n0,1\n")
        self.assertEqual((T.read_lap(d / "empty.csv"), T.read_lap(d / "nogps.csv")), ([], []))

    def test_medoid_drops_partial_and_far_laps(self):
        lap = ll(stadium())
        noisy = ll([(x, y + 1.0) for x, y in stadium()])
        partial = lap[: len(lap) // 3]
        line, used = T.medoid_line([partial, noisy, lap, ll(stadium(1.2))])
        self.assertEqual(used, 2)
        self.assertGreater(len(line), 400)

    def test_similarity_round_trip(self):
        m = T.similarity([(0, 0), (10, 0), (0, 10)], [(5, 5), (5, 15), (-5, 5)])
        self.assertAlmostEqual(math.degrees(math.atan2(m[1], m[0])), 90, places=6)
        p = T.apply(T.invert(m), T.apply(m, (3, 4)))
        self.assertAlmostEqual(p[0], 3)
        self.assertAlmostEqual(p[1], 4)

    def test_pit_names(self):
        self.assertTrue(T.is_pit({"name": "Pit Entry"}))
        self.assertTrue(T.is_pit({"raceway": "pitlane"}))
        self.assertFalse(T.is_pit({"name": "Pit Straight"}))


if __name__ == "__main__":
    unittest.main()
