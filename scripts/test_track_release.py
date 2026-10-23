import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

import track_bundle as B
import track_outlines as T
import track_release as R
from test_track_outlines import ORIGIN, ll, stadium


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

    def test_unpack_takes_only_track_files_and_merge_keeps_one_row_per_track(self):
        with zipfile.ZipFile(self.d / "r.zip", "w") as z:
            z.writestr("circuit/1.json", '{"old":1}')
            z.writestr("background/1.json", "{}")
            z.writestr("circuit/../../evil.json", "{}")  # never written outside out/
            z.writestr("circuit/x.json", "{}")
            z.writestr("quality.json", json.dumps([{"track_id": 1, "coverage": 0.9}]))
            z.writestr("NOTICE.txt", "x")
        out, new = self.d / "out", self.d / "new"
        self.assertEqual(R.unpack(self.d / "r.zip", out), 1)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["1.background.json", "1.circuit.json", "quality.json"])
        self.assertFalse((self.d / "evil.json").exists())
        new.mkdir()
        (new / "2.circuit.json").write_text("{}")
        (new / "2.background.json").write_text("{}")
        (new / "quality.json").write_text(json.dumps([{"track_id": 2, "coverage": 1.0}]))
        R.merge(new, out)
        self.assertEqual([r["track_id"] for r in json.loads((out / "quality.json").read_text())], [1, 2])

    def test_a_release_unpacked_and_bundled_again_has_the_same_geometry_hash(self):
        built = self.d / "built"
        built.mkdir()
        circuit, background = T.build_track(ll(stadium()), [], ORIGIN)
        circuit["quality"]["label"] = "line"
        for tid in (7, 8):
            meta = {"track_id": tid, "built_at": "2026-10-22T00:00:00Z", "line_source": "garage61", "line_laps": 3}
            (built / f"{tid}.circuit.json").write_text(json.dumps({**meta, **circuit}))
            (built / f"{tid}.background.json").write_text(json.dumps({**meta, **background}))
        (built / "quality.json").write_text("[]")
        (self.d / "cat.json").write_text(json.dumps([{"id": 7, "name": "A", "config": ""}, {"id": 8, "name": "B", "config": ""}]))
        bundle = lambda src, out, version: B.cmd_bundle(SimpleNamespace(built=str(src), version=version, commit="c", out=str(out),
                                                                       catalogue=str(self.d / "cat.json"), lines="", previous="", base_release=""))
        bundle(built, self.d / "r1", "a")
        again = self.d / "again"
        R.unpack(self.d / "r1" / "track-outlines-a.zip", again)
        (self.d / "empty").mkdir()
        R.merge(self.d / "empty", again)
        bundle(again, self.d / "r2", "b")
        first, second = (json.loads((self.d / r / "provenance.json").read_text())["content_sha256"] for r in ("r1", "r2"))
        self.assertEqual(first, second)

    def test_new_tracks_without_a_region_are_left_out_once_unless_fictional(self):
        (self.d / "plan.json").write_text(json.dumps({"areas": {"3": {}}}))
        (self.d / "cat.json").write_text(json.dumps([{"id": 3, "name": "A"}, {"id": 4, "name": "B"}, {"id": 384, "name": "iRacing Superspeedway"}]))
        record = self.d / "skipped.json"
        self.assertEqual(R.keep_ids([3, 4, 384], self.d / "plan.json", self.d / "cat.json", record), [3, 384])
        self.assertEqual(json.loads(record.read_text()), {"4": "B"})

    def test_another_format_needs_a_full_rebuild(self):
        (self.d / "p.json").write_text(json.dumps({"format": T.FORMAT}))
        self.assertFalse(R.needs_full(self.d / "p.json"))
        (self.d / "p.json").write_text(json.dumps({"format": T.FORMAT + 1}))
        self.assertTrue(R.needs_full(self.d / "p.json"))


if __name__ == "__main__":
    unittest.main()
