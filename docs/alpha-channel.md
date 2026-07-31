# Alpha application update channel

This repository owns the **application-update** trust record for the Alpha
channel. It is separate from the existing Pocket/model content signing
authority: neither key may authorize the other kind of artifact.

`alpha-channel` accepts only UTF-8 JSON no larger than 64 KiB. The manifest is
closed (unknown and duplicate keys fail), schema `1`, channel `alpha`, and
key ID `alpha-1`. The detached Ed25519 signature is calculated over exactly:

```
TeamManager Alpha Channel v1\x00 + exact alpha.json bytes
```

There is deliberately no checked-in `channels/alpha.json` or signature. An
Alpha channel becomes active only after real immutable installers exist.

Each entry binds product, Windows/amd64, strict `0.x.y-alpha.N` version, tag,
exact 40-lowercase-hex commit, owner/repository, filename, positive bounded
size, lowercase SHA-256, and the sole accepted direct Forgejo HTTPS asset URL:

```
https://forgejo.g-grp.com/Max/<repository>/releases/download/<tag>/<filename>
```

The tag is exactly `v` plus the signed version. URLs with a different
host/path, user info, query, fragment, port, traversal, or escaped ambiguity
are not valid manifest URLs. Consumers must pin the application update
public key and use `verify`; they retain the last accepted sequence and product
versions to reject replay and downgrade. Downloaders must disable redirects and
verify size and SHA-256 after download; this repository intentionally does not
ship a downloader or installer.

`authenticode_policy` is a signed, closed manifest field. Alpha uses
`not-required`; the only other valid value is `required`. This records the
decision without making Authenticode an Alpha release blocker.

## Custody and rotation

The `alpha-1` private key is an external release-custody secret. It is supplied
to the publisher as a raw base64/hex Ed25519 private key or PKCS#8 key file;
never commit, echo, or log it. The public key is separately pinned by each app.
`key_rotation` records the active key window. A later key requires an app update
that pins the successor first, an overlapping signed transition, and a new
schema/key-ID review; no content/model key is a rotation path.

## Offline tooling

Importers that already possess manifest bytes, the detached signature, and a
pinned application public key can use the side-effect-free library:

```
alpha.VerifyTrustTransition(manifest, signature, publicKey, alpha.VerifyOptions{...})
```

It performs no filesystem, network, process, download, installation, or trust
record persistence operation. The consumer owns its retained accepted sequence
and installed versions through `VerifyOptions`.

```
go run ./cmd/alpha-channel verify --manifest candidate.json --signature candidate.json.sig --public-key alpha-update.pub --min-sequence 12
go run ./cmd/alpha-channel verify-candidate --manifest candidate.json --signature candidate.json.sig --public-key alpha-update.pub --race-installer RaceSetup.exe --relay-installer RelaySetup.exe --min-sequence 12
go run ./cmd/alpha-channel publish --manifest candidate.json --private-key external-alpha-1.key --dry-run
```

`verify-candidate` is an offline pre-publication check. After the normal trust
transition succeeds, it checks that each local regular, non-symlink installer
has the signed basename, exact size, and SHA-256 through one opened handle,
then observes the same path identity and size again. Its success is only a
point-in-time observation: it is not an atomic snapshot, lock, stability, or
post-return guarantee. Stage candidates quiescently; a later publisher or
installer must verify the bytes it consumes again. It does not check Forgejo
release existence or immutability, make a public re-download, publish assets,
or authorize channel activation.

`publish` refuses to overwrite `alpha.json` or `alpha.json.sig`; its dry run
still requires the external private key and writes nothing. Real output uses
exclusive create-once file creation. If signature creation fails after the
manifest was created, it removes that manifest; if cleanup itself fails it
reports the partial state and every later publication fails closed rather than
replacing it.

Detached signatures are read with a 4 KiB bound before raw, hex, base64, or PEM
decoding. Public and private key files are local operator inputs; only the
remote channel signature is subject to that transport boundary.

## Later activation sequence

1. Build Race Engineer and Relay from exact Forgejo commits and create their
   immutable tags/releases/assets. Any tag, release, or asset collision fails.
2. Independently public-redownload both assets with redirects disabled; verify
   their sizes and SHA-256 and record the exact commits/tags.
3. Generate the channel manifest with a sequence greater than every accepted
   value, sign it with the external application-update key, and verify it using
   the separately pinned public key.
4. Publish `channels/alpha.json` and `.sig` once. Do not overwrite either.
   Only after that record is independently readable may a later process mirror
   the release to GitHub. This PR creates neither releases nor a live channel.
