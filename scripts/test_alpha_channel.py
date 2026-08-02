import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("alpha_channel.py")
SPEC = importlib.util.spec_from_file_location("alpha_channel", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

CHANNEL = {
    "version": "1", "channel": "alpha", "generated_at": "2026-08-02T08:00:00Z",
    "assets": [
        {"component": "race-engineer-go", "version": "v0.3.0-alpha.1", "release_tag": "v0.3.0-alpha.1", "asset_name": "race-engineer-go-windows-amd64.zip", "url": "https://forgejo.g-grp.com/Max/race-engineer-go/releases/download/v0.3.0-alpha.1/race-engineer-go-windows-amd64.zip", "size_bytes": 1, "sha256": "a" * 64},
        {"component": "teammanager-relay", "version": "v0.3.0-alpha.1", "release_tag": "v0.3.0-alpha.1", "asset_name": "teammanager-relay-windows-amd64.zip", "url": "https://forgejo.g-grp.com/Max/teammanager-relay/releases/download/v0.3.0-alpha.1/teammanager-relay-windows-amd64.zip", "size_bytes": 2, "sha256": "b" * 64},
    ],
}


class AlphaChannelTests(unittest.TestCase):
    def write(self, root: Path, value: object) -> Path:
        channel = root / "alpha.json"
        channel.write_text(json.dumps(value), encoding="utf-8")
        return channel

    def test_accepts_closed_two_asset_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            module.load_and_validate(self.write(Path(temp), CHANNEL))

    def test_builder_emits_the_canonical_ordered_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "alpha.json"
            args = type("Args", (), {
                "output": output, "generated_at": CHANNEL["generated_at"],
                "race_engineer_go_release_tag": CHANNEL["assets"][0]["release_tag"],
                "race_engineer_go_asset_name": CHANNEL["assets"][0]["asset_name"],
                "race_engineer_go_size_bytes": "1", "race_engineer_go_sha256": "a" * 64,
                "teammanager_relay_release_tag": CHANNEL["assets"][1]["release_tag"],
                "teammanager_relay_asset_name": CHANNEL["assets"][1]["asset_name"],
                "teammanager_relay_size_bytes": "2", "teammanager_relay_sha256": "b" * 64,
            })()
            module.build(args)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), CHANNEL)
            module.load_and_validate(output)

    def test_rejects_tampered_or_noncanonical_asset_identity(self):
        cases = []
        unknown = copy.deepcopy(CHANNEL); unknown["extra"] = True; cases.append(unknown)
        wrong_order = copy.deepcopy(CHANNEL); wrong_order["assets"].reverse(); cases.append(wrong_order)
        query = copy.deepcopy(CHANNEL); query["assets"][0]["url"] += "?token=no"; cases.append(query)
        asset_swap = copy.deepcopy(CHANNEL); asset_swap["assets"][0]["url"] = asset_swap["assets"][0]["url"].replace("race-engineer-go", "teammanager-relay"); cases.append(asset_swap)
        size = copy.deepcopy(CHANNEL); size["assets"][1]["size_bytes"] = "2"; cases.append(size)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for value in cases:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        module.load_and_validate(self.write(root, value))


if __name__ == "__main__":
    unittest.main()
