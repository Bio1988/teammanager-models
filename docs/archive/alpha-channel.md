# Historical Alpha application update channel

> **HISTORICAL — SUPERSEDED.** This document records the abandoned signed
> public application-update-channel design. The private Alpha now serves
> authenticated release metadata and the next complete installer through
> TeamManager Server. `teammanager-models` owns no application-update channel
> or runtime trust authority. Everything below is retained only as historical
> evidence.

## Former design

This repository previously owned an **application-update** trust record for
the Alpha channel. It was separate from the Pocket/model content signing
authority: neither key could authorize the other kind of artifact.

`alpha-channel` accepted only UTF-8 JSON no larger than 64 KiB. The manifest
was closed (unknown and duplicate keys failed), schema `1`, channel `alpha`,
and key ID `alpha-1`. The detached Ed25519 signature was calculated over
exactly:

```
TeamManager Alpha Channel v1\x00 + exact alpha.json bytes
```

There was deliberately no checked-in `channels/alpha.json` or signature. An
Alpha channel would have become active only after real immutable installers
existed.

Each entry bound product, Windows/amd64, strict `0.x.y-alpha.N` version, tag,
exact 40-lowercase-hex commit, owner/repository, filename, positive bounded
size, lowercase SHA-256, and the sole accepted direct Forgejo HTTPS asset URL:

```
https://forgejo.g-grp.com/Max/<repository>/releases/download/<tag>/<filename>
```

The tag was exactly `v` plus the signed version. URLs with a different
host/path, user info, query, fragment, port, traversal, or escaped ambiguity
were not valid manifest URLs. Consumers pinned the application-update public
key and used `verify`; they retained the last accepted sequence and product
versions to reject replay and downgrade. Downloaders disabled redirects and
verified size and SHA-256 after download; this repository intentionally did
not ship a downloader or installer.

`authenticode_policy` was a signed, closed manifest field. Alpha used
`not-required`; the only other valid value was `required`. This recorded the
decision without making Authenticode an Alpha release blocker.

## Former custody and rotation notes

The `alpha-1` private key was an external release-custody secret. It was
supplied to the publisher as a raw base64/hex Ed25519 private key or PKCS#8
key file; it was never to be committed, echoed, or logged. The public key was
separately pinned by each app. `key_rotation` recorded the active key window.
A later key would have required an app update that pinned the successor first,
an overlapping signed transition, and a new schema/key-ID review; no
content/model key was a rotation path.

## Former offline tooling

Importers that already possessed manifest bytes, the detached signature, and
a pinned application public key could use the side-effect-free library:

```
alpha.VerifyTrustTransition(manifest, signature, publicKey, alpha.VerifyOptions{...})
```

It performed no filesystem, network, process, download, installation, or
trust-record persistence operation. The consumer owned its retained accepted
sequence and installed versions through `VerifyOptions`.

```
go run ./cmd/alpha-channel verify --manifest candidate.json --signature candidate.json.sig --public-key alpha-update.pub --min-sequence 12
go run ./cmd/alpha-channel verify-candidate --manifest candidate.json --signature candidate.json.sig --public-key alpha-update.pub --race-installer RaceSetup.exe --relay-installer RelaySetup.exe --min-sequence 12
go run ./cmd/alpha-channel publish --manifest candidate.json --private-key external-alpha-1.key --dry-run
```

`verify-candidate` was an offline pre-publication check. After the normal
trust transition succeeded, it checked that each local regular, non-symlink
installer had the signed basename, exact size, and SHA-256 through one opened
handle, then observed the same path identity and size again. Its success was
only a point-in-time observation: it was not an atomic snapshot, lock,
stability, or post-return guarantee. Stage candidates quiescently; a later
publisher or installer had to verify the bytes it consumed again. It did not
check Forgejo release existence or immutability, make a public re-download,
publish assets, or authorize channel activation.

`publish` refused to overwrite `alpha.json` or `alpha.json.sig`; its dry run
still required the external private key and wrote nothing. Real output used
exclusive create-once file creation. If signature creation failed after the
manifest was created, it removed that manifest; if cleanup itself failed it
reported the partial state and every later publication failed closed rather
than replacing it.

Detached signatures were read with a 4 KiB bound before raw, hex, base64, or
PEM decoding. Public and private key files were local operator inputs; only
the remote channel signature was subject to that transport boundary.

## Former activation sequence

1. Build Race Engineer and Relay from exact Forgejo commits and create their
   immutable tags/releases/assets. Any tag, release, or asset collision fails.
2. Independently public-redownload both assets with redirects disabled; verify
   their sizes and SHA-256 and record the exact commits/tags.
3. Generate the channel manifest with a sequence greater than every accepted
   value, sign it with the external application-update key, and verify it using
   the separately pinned public key.
4. Publish `channels/alpha.json` and `.sig` once. Do not overwrite either.
   Only after that record was independently readable could a later process
   mirror the release to GitHub. This former design created neither releases
   nor a live channel.
