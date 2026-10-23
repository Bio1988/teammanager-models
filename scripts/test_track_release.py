import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import track_release as R


class ReleaseHelpersTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_new_ids_are_catalogue_tracks_with_a_line_missing_from_the_release(self):
        (self.d / "prov.json").write_text(json.dumps({"tracks": [1, 2]}))
        (self.d / "cat.json").write_text(json.dumps([{"id": i} for i in (1, 2, 3, 4)]))
        (self.d / "lines").mkdir()
        for i in (1, 3, 9):  # 9 is no catalogue track (any more)
            (self.d / "lines" / f"{i}.line.json").write_text("{}")
        self.assertEqual(R.new_ids(self.d / "prov.json", self.d / "cat.json", self.d / "lines"), [3])

    def test_unpack_and_merge_keep_one_set_of_files_and_quality_rows_per_track(self):
        with zipfile.ZipFile(self.d / "r.zip", "w") as z:
            z.writestr("circuit/1.json", '{"old":1}')
            z.writestr("background/1.json", "{}")
            z.writestr("quality.json", json.dumps([{"track_id": 1, "coverage": 0.9}]))
            z.writestr("NOTICE.txt", "x")
        out, new = self.d / "out", self.d / "new"
        self.assertEqual(R.unpack(self.d / "r.zip", out), 1)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["1.background.json", "1.circuit.json", "quality.json"])
        new.mkdir()
        (new / "2.circuit.json").write_text("{}")
        (new / "2.background.json").write_text("{}")
        (new / "quality.json").write_text(json.dumps([{"track_id": 2, "coverage": 1.0}]))
        R.merge(new, out)
        self.assertEqual([r["track_id"] for r in json.loads((out / "quality.json").read_text())], [1, 2])
        self.assertTrue((out / "2.circuit.json").exists())


if __name__ == "__main__":
    unittest.main()
