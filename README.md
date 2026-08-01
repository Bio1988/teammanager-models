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
maintainer may manually dispatch `publish-model-manifest` from `main`, supplying
the exact reviewed, successful `main` SHA. It checks the actual checkout, the
branch API, and the commit-status API before handling a signing key. The final
tag is reserved at that SHA, a draft release is uploaded, and its release API
metadata is checked for the exact three names, IDs, and byte sizes. Forgejo's
automatic task token cannot read draft binaries, so full byte/signature/hash
verification occurs immediately after publish through fresh anonymous downloads.
A failure triggers a best-effort return of the release to draft.

The workflow consumes the existing base64 signing-key and public-key secrets.
It uses Forgejo's ephemeral, same-repository automatic `FORGEJO_TOKEN`. Forgejo
16 does not enforce GitHub-style per-workflow `permissions` narrowing for this
token: it has broad write capability within this repository's units. This
workflow contains that platform limitation with manual-only dispatch, protected
main, SHA/status checks, no persisted checkout credentials, immutable action
pinning, and no API writes except the reserved tag and its release. Branch
protection cannot prove that direct pushes are disabled or that no privileged
user can bypass it; that remains an external owner audit. If that is
not acceptable, publication must instead wait for a dedicated minimally scoped
release credential or an Authorized Integration policy.

Strict server-byte verification before publication requires a maintainer PAT or
an Authorized Integration with that capability. The automatic-token path has a
brief, fail-closed public-verification window: it re-drafts on failure but cannot
guarantee that a public observer did not see the failed publication.

External prerequisite: `main` must be protected with at least one required PR
approval and one required status-check context. The current repository reports
`protected: false`, `required_approvals: 0`, and `enable_status_check: false`,
so the workflow will fail closed until an owner configures that protection.
Failures after draft creation intentionally leave the draft and its tag for
maintainer inspection, while temporary key material is removed by the shell
cleanup trap.

## Current consumer contract

`manifest.json` retains the current Pocket default, optional English language/catalog
packs, and clone compatibility metadata because Race Engineer consumes them in
its published release format. No separate voice/TTS planning catalog remains.
