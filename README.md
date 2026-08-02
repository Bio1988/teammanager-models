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
maintainer may manually dispatch `sign-model-manifest-candidate` from `main`,
supplying the exact reviewed, successful `main` SHA. Before it receives either
repository secret, it checks the dispatch ref, actual checkout, branch API, and
commit-status API. `main` must be protected with at least one required PR
approval and one required status-check context.

The workflow uses the existing base64 signing-key and public-key secrets only in
the signing step. It creates and locally verifies the three R3.2 contract files:
the exact manifest, its detached Ed25519 signature, and its SHA-256 sidecar. It
then retains these files and `candidate-evidence.json` as an Actions artifact.
The evidence names the immutable source SHA and explicitly records
`publication.status` as `not-attempted`.

This is deliberately not a publisher: it has no Forgejo token, tag, release,
upload, or repository-write step. A maintainer must separately establish the
signing-custody boundary (trusted runner; dispatch/ref access limited to signing
custodians; protected `main` with review and exact status contexts) and approve
a publication mechanism before any candidate can be represented as a release.

## Current consumer contract

`manifest.json` retains the current Pocket default, optional English language/catalog
packs, and clone compatibility metadata because Race Engineer consumes them in
its published release format. No separate voice/TTS planning catalog remains.
