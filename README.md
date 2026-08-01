# TeamManager Models

`manifest.json` is the source catalog for the active managed Pocket bundles.
Retired generic model, Chatterbox, KoboldCPP, voice-profile, voice/TTS planning,
and duplicate checksum catalogs are deliberately not kept here.

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

The obsolete one-shot English MVP publisher was removed after Pocket R3 replaced
its inputs and immutable release tag. Existing release assets remain unchanged.
Any future asset release needs a small current publication path reviewed against
the then-active manifest and consumers; no private key belongs in this repository.

## Manifest publication

After this workflow is reviewed and merged to Forgejo `main`, an authorized
maintainer may manually dispatch `publish-model-manifest` from that exact main
branch. It rejects any non-main or no-longer-current commit, signs the exact
checked-out `manifest.json`, creates the draft-only immutable
`teammanager-model-manifest-v3-pocket-r3.2` release, and publishes it only
after an unauthenticated release download byte-compares and verifies.

The workflow consumes the existing base64 signing-key and public-key secrets.
It uses Forgejo's ephemeral, repository-scoped automatic `FORGEJO_TOKEN` for
the same-repository release API; no long-lived release-token secret is needed.
Failures after draft creation intentionally leave that draft for maintainer
inspection, while temporary key material is removed by the shell cleanup trap.

## Current consumer contract

`manifest.json` retains the current Pocket default, optional English language/catalog
packs, and clone compatibility metadata because Race Engineer consumes them in
its published release format. No separate voice/TTS planning catalog remains.
