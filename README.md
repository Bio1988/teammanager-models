# TeamManager Models

`manifest.json` is the source catalog for the active managed Pocket bundles.
Retired generic model, Chatterbox, KoboldCPP, voice-profile, voice/TTS planning,
and duplicate checksum catalogs are deliberately not kept here.

## Release integrity

The publisher produces one versioned manifest release plus two integrity
companions:

- `<manifest>.sig`: one Ed25519 signature over the exact manifest bytes;
- `<manifest>.sha256`: SHA-256 for transport integrity.

Race Engineer fetches those three files from the same versioned Forgejo release
when Pocket compatibility metadata is present. Individual artifacts retain their
own SHA-256 fields in `manifest.json`. The source checkout deliberately has no
signature or hash sidecar: only a published, versioned release is an installable
manifest authority.

Managed Whisper remains protected by its runtime release manifest and the
installer's archive/model SHA-256 checks. It does not consume a separate Models
repository authority object.

## Publication

`scripts/publish-pocket-model-manifest.py` derives the active English Pocket
compatibility values from the three reviewed Pocket archives, creates the signed
versioned manifest, verifies it, and publishes the three release files. No
private key is stored in this repository.

```sh
python3 -m unittest discover -s scripts -p "test_*.py"
```

## Current consumer contract

`manifest.json` retains the current Pocket default, optional language/catalog
packs, and clone compatibility metadata because Race Engineer consumes them in
its published release format. No separate voice/TTS planning catalog remains.
