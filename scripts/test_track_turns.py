import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

import track_turns as T
from test_track_outlines import ORIGIN, ll, stadium

HAS_SVG = importlib.util.find_spec("svgelements") is not None


def to_svg(p, scale=2.0, degrees=40.0):
    """A lap point (metres) as the iRacing SVG would hold it: rotated, in pixels, y flipped back by the reader."""
    r = math.radians(degrees)
    x, y = p
    return ((x * math.cos(r) - y * math.sin(r)) / scale + 900, (x * math.sin(r) + y * math.cos(r)) / scale + 500)


def turn(number, apex, label=None):
    return {"number": number, "label": label or str(number), "apex_pct": apex}


class TurnsTest(unittest.TestCase):
    def tmp(self):
        return Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_svg_fit_and_turn_positions_follow_the_lap(self):
        lap = stadium()
        m, error = T.fit_svg(T.decimate([to_svg(p) for p in lap[::3]], 150), T.decimate(lap, 250))
        self.assertLess(error, 8.0)  # nearest-sample distance between two point sets 5-15 m apart
        self.assertAlmostEqual(math.hypot(m[0], m[1]), 2.0, delta=0.05)  # metres per SVG pixel
        quarter, half = lap[len(lap) // 4], lap[len(lap) // 2]
        along = lambda i: T.length(lap[: i + 1]) / T.length(lap + lap[:1])
        # labels a little off the line, as iRacing draws them; only turn-like labels count
        labels = [("2", *to_svg((half[0], half[1] + 8))), ("1", *to_svg((quarter[0] + 8, quarter[1]))),
                  ("Pit", 0.0, 0.0), ("100R", *to_svg(quarter)), ("TV3", *to_svg(quarter)), ("1", *to_svg((quarter[0] + 8, quarter[1])))]
        turns = T.place_turns(labels, m, lap)
        self.assertEqual([t["label"] for t in turns], ["1", "2"])  # the duplicate "1" counts once
        self.assertAlmostEqual(turns[0]["apex_pct"], along(len(lap) // 4), delta=0.01)
        self.assertAlmostEqual(turns[1]["apex_pct"], along(len(lap) // 2), delta=0.01)

    def test_lap_order_counts_the_wrap_once_and_close_swaps_are_fixed(self):
        self.assertEqual(T.inversions([turn(5, .1), turn(6, .4), turn(1, .6), turn(2, .9)]), 0)  # start/finish mid-lap
        swapped = [turn(1, .10), turn(3, .200), turn(2, .205), turn(4, .5)]
        self.assertEqual(T.inversions(swapped), 1)
        fixed = T.fix_close_order(swapped, 5000)  # .200 and .205 are 25 m apart
        self.assertEqual([(t["number"], t["apex_pct"]) for t in fixed], [(1, .1), (2, .2), (3, .205), (4, .5)])
        far = [turn(1, .1), turn(3, .2), turn(2, .4), turn(4, .5)]  # 1 km apart: a real error, kept and counted
        self.assertEqual(T.inversions(T.fix_close_order(far, 5000)), 1)

    def test_text_spans_are_one_label(self):
        d = self.tmp()
        (d / "turns.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text transform="matrix(1 0 0 1 10 20)">'
                                     '<tspan x="0" y="0">1</tspan><tspan x="7" y="0">1</tspan></text>'
                                     '<text x="5" y="6">3a</text><text transform="translate(1602.99 718.33)">4</text></svg>')
        self.assertEqual(T.svg_labels(d / "turns.svg"), [("11", 10.0, -20.0), ("3a", 5.0, -6.0), ("4", 1602.99, -718.33)])

    @unittest.skipUnless(HAS_SVG, "svgelements not installed")
    def test_place_writes_turns_in_lap_order_and_survives_a_broken_svg(self):
        d = self.tmp()
        lap = stadium()
        (d / "lines").mkdir()
        (d / "svg").mkdir()
        (d / "built").mkdir()
        for tid in (7, 8):
            (d / "lines" / f"{tid}.line.json").write_text(json.dumps({"line": ll(lap)}))
            (d / "built" / f"{tid}.circuit.json").write_text(json.dumps({"track_id": tid, "quality": {}}))
        pts = [to_svg((x, -y)) for x, y in lap[::2]]  # the reader flips y back
        path = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
        (d / "svg" / "7.active.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg"><path d="{path}"/></svg>')
        texts = "".join(f'<text transform="matrix(1 0 0 1 {x:.2f} {y:.2f})">{k}</text>'
                        for k, (x, y) in ((1, to_svg((lap[100][0], -lap[100][1]))), (2, to_svg((lap[300][0], -lap[300][1])))))
        (d / "svg" / "7.turns.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{texts}</svg>')
        (d / "svg" / "8.active.svg").write_text("<svg")  # broken
        (d / "svg" / "8.turns.svg").write_text("<svg/>")
        T.cmd_place(type("A", (), {"built": str(d / "built"), "lines": str(d / "lines"), "svg": str(d / "svg"), "ids": ""})())
        good = json.loads((d / "built" / "7.circuit.json").read_text())
        self.assertEqual([t["label"] for t in good["turns"]], ["1", "2"])
        self.assertEqual(good["turns_fit"]["inversions"], 0)
        self.assertNotIn("turns", json.loads((d / "built" / "8.circuit.json").read_text()))
        rows = {r["track_id"]: r for r in json.loads((d / "built" / "turns-quality.json").read_text())}
        self.assertIn("error", rows[8])


if __name__ == "__main__":
    unittest.main()
