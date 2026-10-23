import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

import track_turns as T
from test_track_outlines import stadium


def to_svg(p, scale=2.0, degrees=40.0):
    """A lap point (metres) as the iRacing SVG would hold it: rotated, in pixels, y flipped back by the reader."""
    r = math.radians(degrees)
    x, y = p
    return ((x * math.cos(r) - y * math.sin(r)) / scale + 900, (x * math.sin(r) + y * math.cos(r)) / scale + 500)


class TurnsTest(unittest.TestCase):
    def test_svg_fit_and_turn_positions_follow_the_lap(self):
        lap = stadium()
        svg = [to_svg(p) for p in lap[::3]]
        m, error = T.fit_svg(T.decimate(svg, 150), T.decimate(lap, 250))
        self.assertLess(error, 8.0)  # nearest-sample distance between two point sets 5-15 m apart
        self.assertAlmostEqual(math.hypot(m[0], m[1]), 2.0, delta=0.05)  # metres per SVG pixel
        # labels a little off the line, as iRacing draws them; "2" is placed before "1" in the SVG on purpose
        quarter, half = lap[len(lap) // 4], lap[len(lap) // 2]
        along = lambda i: T.length(lap[: i + 1]) / T.length(lap)
        labels = [("2", *to_svg((half[0], half[1] + 8))), ("1", *to_svg((quarter[0] + 8, quarter[1]))), ("Pit", 0.0, 0.0)]
        turns = T.place_turns(labels, m, lap)
        numbered = turns
        self.assertEqual([t["label"] for t in turns], ["1", "2"])  # "Pit" is no turn
        self.assertAlmostEqual(numbered[0]["apex_pct"], along(len(lap) // 4), delta=0.01)
        self.assertAlmostEqual(numbered[1]["apex_pct"], along(len(lap) // 2), delta=0.01)

    @unittest.skipUnless(importlib.util.find_spec("svgelements"), "svgelements not installed")
    def test_svg_reading(self):
        d = Path(tempfile.mkdtemp())
        (d / "active.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0,0 L60,0 C60,60 0,60 0,0z"/></svg>')
        (d / "turns.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><text transform="matrix(1 0 0 1 10 20)">3</text>'
                                     '<text x="5" y="6">a long caption</text></svg>')
        pts = T.svg_points(d / "active.svg")
        self.assertGreater(len(pts), 10)
        self.assertTrue(all(y <= 0 for _, y in pts))  # y flipped to point north
        self.assertEqual(T.svg_labels(d / "turns.svg"), [("3", 10.0, -20.0)])


if __name__ == "__main__":
    unittest.main()
