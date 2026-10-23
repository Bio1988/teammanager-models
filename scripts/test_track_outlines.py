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

    def test_an_implausible_fit_is_dropped(self):
        self.setUp(degrees=3.0)  # beyond any measured iRacing offset: these would be the wrong roads
        circuit, _ = T.build_track(self.line, self.elements, ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["rotation_deg"], 0)

    def test_without_roads_keeps_the_line_and_says_so(self):
        circuit, _ = T.build_track(self.line, [], ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["coverage"], 0)
        self.assertGreater(len(circuit["outline"]), 10)


class BundleTest(unittest.TestCase):
    def test_bundle_is_reproducible_and_carries_provenance(self):
        built = Path(tempfile.mkdtemp())
        circuit, background = T.build_track(ll(stadium()), [], ORIGIN)
        circuit["quality"]["coverage"] = 0.95
        meta = {"track_id": 7, "built_at": "2026-10-22T00:00:00Z", "line_source": "garage61", "line_laps": 3, "osm_timestamp": "2026-10-21T20:00:00Z"}
        (built / "7.circuit.json").write_text(json.dumps({**meta, **circuit}))
        (built / "7.background.json").write_text(json.dumps({**meta, **background}))
        (built / "quality.json").write_text("[]")
        digests = []
        for _ in range(2):
            out = Path(tempfile.mkdtemp())
            T.cmd_bundle(SimpleNamespace(built=str(built), version="t1", commit="abc", out=str(out), min_coverage=0.9))
            digests.append((out / "SHA256SUMS").read_text())
        self.assertEqual(digests[0], digests[1])
        provenance = json.loads((out / "provenance.json").read_text())
        self.assertEqual(provenance["tracks"], [7])
        self.assertEqual(provenance["skipped_low_coverage"], [])
        self.assertEqual(provenance["line_sources"], {"garage61": 1})
        self.assertIn(provenance["sha256"], digests[0])
        with zipfile.ZipFile(out / "track-outlines-t1.zip") as z:
            self.assertEqual(z.namelist(), ["circuit/7.json", "background/7.json", "quality.json", "NOTICE.txt"])
            self.assertIn(b"OpenStreetMap contributors", z.read("NOTICE.txt"))


    def test_low_coverage_tracks_are_left_out_and_an_empty_bundle_fails(self):
        built = Path(tempfile.mkdtemp())
        circuit, background = T.build_track(ll(stadium()), [], ORIGIN)
        for tid, coverage in ((7, 0.95), (8, 0.5)):
            circuit["quality"]["coverage"] = coverage
            meta = {"track_id": tid, "built_at": "2026-10-22T00:00:00Z", "line_source": "garage61", "line_laps": 3, "osm_timestamp": ""}
            (built / f"{tid}.circuit.json").write_text(json.dumps({**meta, **circuit}))
            (built / f"{tid}.background.json").write_text(json.dumps({**meta, **background}))
        (built / "quality.json").write_text("[]")
        out = Path(tempfile.mkdtemp())
        T.cmd_bundle(SimpleNamespace(built=str(built), version="t1", commit="abc", out=str(out), min_coverage=0.9))
        provenance = json.loads((out / "provenance.json").read_text())
        self.assertEqual((provenance["tracks"], provenance["skipped_low_coverage"]), ([7], [8]))
        with self.assertRaises(SystemExit):
            T.cmd_bundle(SimpleNamespace(built=str(built), version="t2", commit="abc", out=str(Path(tempfile.mkdtemp())), min_coverage=0.99))


class LinesTest(unittest.TestCase):
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
