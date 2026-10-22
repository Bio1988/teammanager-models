import hashlib
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

import osm_extract as X

BODY = bytes(range(256)) * 4096  # 1 MiB
DATED = "/north-america/us/alabama-261020.osm.pbf"


class Geofabrik(http.server.BaseHTTPRequestHandler):
    """`-latest` redirects (307) to the dated file; the dated file and its .md5 serve Range requests."""

    gets = []

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.answer(body=False)

    def do_GET(self):
        self.answer(body=True)

    def answer(self, body):
        if self.path.startswith("/north-america/us/alabama-latest.osm.pbf"):
            self.send_response(307)
            self.send_header("Location", self.path.replace("-latest", "-261020"))
            self.end_headers()
            return
        if self.path == DATED + ".md5":
            data = f"{hashlib.md5(BODY).hexdigest()}  alabama-latest.osm.pbf\n".encode()
        elif self.path == DATED:
            data = BODY
            if body:
                Geofabrik.gets.append(self.headers.get("Range"))
        else:
            self.send_error(404)
            return
        start = int(self.headers.get("Range", "bytes=0-")[6:].rstrip("-") or 0)
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(data) - start))
        self.end_headers()
        if body:
            self.wfile.write(data[start:])


class FetchTest(unittest.TestCase):
    def setUp(self):
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Geofabrik)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/north-america/us/alabama-latest.osm.pbf"
        self.dir = Path(tempfile.mkdtemp())
        Geofabrik.gets = []

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_follows_the_redirect_and_skips_an_unchanged_file(self):
        dest = self.dir / X.pbf_name("us/alabama")
        self.assertEqual(dest.name, "us-alabama.osm.pbf")
        self.assertEqual(X.fetch(self.url, dest, pause=0), "downloaded")
        self.assertEqual(dest.read_bytes(), BODY)
        self.assertEqual(X.fetch(self.url, dest, pause=0), "current")
        self.assertEqual(Geofabrik.gets, [None])  # the second call compared the MD5 only
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["us-alabama.osm.pbf"])

    def test_resumes_only_the_same_dated_file(self):
        dest = self.dir / X.pbf_name("us/alabama")
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(BODY[:1000])
        dest.with_name(dest.name + ".part-url").write_text(self.url.replace("-latest", "-261020"))
        self.assertEqual(X.fetch(self.url, dest, pause=0), "downloaded")
        self.assertEqual(Geofabrik.gets, ["bytes=1000-"])
        self.assertEqual(dest.read_bytes(), BODY)

        dest.unlink()
        part.write_bytes(b"x" * 1000)  # left over from an older snapshot
        dest.with_name(dest.name + ".part-url").write_text("http://old/alabama-261001.osm.pbf")
        Geofabrik.gets = []
        self.assertEqual(X.fetch(self.url, dest, pause=0), "downloaded")
        self.assertEqual(Geofabrik.gets, [None])
        self.assertEqual(dest.read_bytes(), BODY)


if __name__ == "__main__":
    unittest.main()
