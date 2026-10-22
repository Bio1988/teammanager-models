import math
import unittest

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
    def setUp(self):
        # OSM is the lap rotated by 0.5 deg about (400, 200) and shifted 25 m east and north: iRacing's frame is off
        r = math.radians(0.5)
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

    def test_without_roads_keeps_the_line_and_says_so(self):
        circuit, _ = T.build_track(self.line, [], ORIGIN)
        self.assertFalse(circuit["quality"]["aligned"])
        self.assertEqual(circuit["quality"]["coverage"], 0)
        self.assertGreater(len(circuit["outline"]), 10)


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
