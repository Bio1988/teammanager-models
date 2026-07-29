# TeamManager Models

`manifest.json` is the source catalog for the active managed Pocket bundles.
Retired generic model, Chatterbox, KoboldCPP, voice-profile, voice/TTS planning,
and duplicate checksum catalogs are deliberately not kept here.

`manifest-v4.candidate.json` is preparation for one future Pocket-and-Whisper
catalog. It is **unpublished, unsigned, and not a runtime authority**. No current
Race Engineer or installer consumes it. It becomes installable only after the
owner approves its exact bytes, publishes those bytes in an immutable Forgejo
release with the one supported signature and SHA-256 companion, and a separately
reviewed Race Engineer change selects that release URL.

The candidate lists each downloadable artifact once. Profiles and optional
language packs refer to asset IDs instead of copying archive records. The active
`manifest.json`, published Pocket R3 release, Whisper manifests, and existing
client behavior remain unchanged by this preparation.

## Release integrity

The active Pocket R3 release contains one versioned manifest plus two integrity
companions:

- `<manifest>.sig`: one Ed25519 signature over the exact manifest bytes;
- `<manifest>.sha256`: SHA-256 for transport integrity.

Race Engineer fetches those three files from the same versioned Forgejo release
when Pocket compatibility metadata is present. Individual artifacts retain their
own SHA-256 fields in `manifest.json`. The source checkout deliberately has no
signature or hash sidecar: only the already published, versioned R3 release is
installable.

Managed Whisper remains protected by its runtime release manifest and the
installer's archive/model SHA-256 checks. It does not consume a separate Models
repository authority object.

## Validation

```sh
python3 -m unittest discover -s scripts -p "test_*.py"
```

The semantic candidate checks are test-only. They deliberately use Python's
standard JSON and URL libraries, tolerate unknown additive fields, and reject
duplicate IDs or references, unsafe paths, foreign/non-release URLs, invalid
sizes, and non-lowercase SHA-256 values. They are not a second runtime parser or
signing mechanism.

The obsolete one-shot English MVP publisher was removed after Pocket R3 replaced
its inputs and immutable release tag. Existing release assets remain unchanged.
Any future asset release needs a small current publication path reviewed against
the then-active manifest and consumers; no private key belongs in this repository.

## Current consumer contract

`manifest.json` retains the current Pocket default, optional language/catalog
packs, and clone compatibility metadata because Race Engineer consumes them in
its published release format. No separate voice/TTS planning catalog remains.
