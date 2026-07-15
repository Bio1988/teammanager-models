# Pocket TTS multilingual R1 attribution and release staging

## Publication status

These 10 deterministic archives are prepared locally only. They have **not been uploaded or published** to Forgejo. The URLs staged in `manifest.json` are the intended canonical destinations, not evidence that the assets are currently available.

Do not publish or announce release `pocket-tts-multilang-v2.1.0-r1` until every archive has been uploaded and the downloaded Forgejo asset has been verified against the recorded byte size and SHA-256 digest. The canonical release asset prefix is:

`https://forgejo.g-grp.com/Max/teammanager-models/releases/download/pocket-tts-multilang-v2.1.0-r1/`

## Provenance and attribution

- Upstream: `kyutai/pocket-tts`
- Upstream revision: `4c8ad48f8a003909bc4f1122cbe88a4252124621`
- Package version: `2.1.0`
- Package revision: `multilang-r1`
- Platform: `windows-amd64-cpu`
- License: CC-BY-4.0 with upstream model-card terms
- Attribution: Kyutai Pocket TTS, CC-BY-4.0; TeamManager packaging only, unmodified model weights.
- Builder: `scripts/build-pocket-language-artifacts.py`
- Local receipt: `/tmp/teammanager-pocket-language-release-r1/pocket-languages-multilang-r1-receipt.json`

The receipt records `publication_performed: false`. It is the source of the manifest fragments, archive inventory, sizes, hashes, layout metadata, license, and attribution.

## Staged artifact inventory

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `pocket-language-english-multilang-r1.zip` | 174919599 | `584739bb6aa13c21aa9cef8dcdbd382583273cc87e5406751717581ecfd877f8` |
| `pocket-language-german-multilang-r1.zip` | 174493125 | `0b40a1b868a6b5f36649b6078d16094b53059b122dcf7820973346ad4d08f83d` |
| `pocket-language-italian-multilang-r1.zip` | 174761575 | `4add8bf4a3cfa08f258768a65adeed0a97d95cbaef746f605601a560047be8f2` |
| `pocket-language-portuguese-multilang-r1.zip` | 174821657 | `56cdf4f32caca2fc0701f66d90ccf40b8a40863a80ebd3cbc428d9ec5ec7dd30` |
| `pocket-language-spanish-multilang-r1.zip` | 174792128 | `77dc699359ea821ac8cb146db3c1c552352a0300d8eb905ba5271b3844ebef37` |
| `pocket-language-french_24l-multilang-r1.zip` | 535708026 | `618fa5e422afc8f587f265ebef8356d3be85b845e1ee63eba334221df4b02de3` |
| `pocket-language-german_24l-multilang-r1.zip` | 535731619 | `c6bcdad0ae8cdf13c91bd2379f48903259ad2f15c9eef94de5fc02b34ab674b8` |
| `pocket-language-italian_24l-multilang-r1.zip` | 535895963 | `b0ec86cc5e8ff1665d2e33243e8153b7de445acde5ce2ce9941dfdf758609447` |
| `pocket-language-portuguese_24l-multilang-r1.zip` | 536099203 | `f93502563f4e722bf9c00de849d6bfcc24ba3fecea27d7f021d734f00e080527` |
| `pocket-language-spanish_24l-multilang-r1.zip` | 535993679 | `37e62939b5c15b2c223739aab45715d753b1ed52de0f69fb086964d98b7570ce` |

Inventory totals: 10 archives, 3,553,216,574 bytes, and 40 ZIP members. The merged manifest contains 10 `assets.pocket_bundles.language_packs` records and the same 10 archives in `assets.pocket_bundles.optional`. No generated fragment targets `assets.voice_tts_library`, so its 33 catalog entries remain unchanged.

## Publication gate

1. Re-run `sha256sum -c SHA256SUMS` and ZIP integrity checks in the local staging directory.
2. Upload exactly the 10 archives above under the canonical Forgejo release tag and filenames.
3. Download each staged Forgejo asset from its canonical URL and verify its byte size and SHA-256 digest against this inventory and the receipt.
4. Verify all 10 manifest URLs resolve to the expected assets before treating the release or manifest entries as published.