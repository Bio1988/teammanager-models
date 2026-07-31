package main

import (
	"crypto/ed25519"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"forgejo.g-grp.com/Max/teammanager-models/alpha"
)

func main() {
	if len(os.Args) < 2 {
		die("usage: alpha-channel verify|publish")
	}
	switch os.Args[1] {
	case "verify":
		verifyCmd(os.Args[2:])
	case "publish":
		publishCmd(os.Args[2:])
	default:
		die("usage: alpha-channel verify|publish")
	}
}
func verifyCmd(args []string) {
	fs := flag.NewFlagSet("verify", flag.ExitOnError)
	mf := fs.String("manifest", "", "manifest path")
	sig := fs.String("signature", "", "detached signature path")
	key := fs.String("public-key", "", "pinned application update public key")
	min := fs.Uint64("min-sequence", 0, "last accepted sequence")
	rv := fs.String("race-version", "", "installed race version")
	lv := fs.String("relay-version", "", "installed relay version")
	fs.Parse(args)
	if *mf == "" || *sig == "" || *key == "" {
		die("--manifest, --signature, and --public-key are required")
	}
	b, err := readManifest(*mf)
	must(err)
	s, err := readSignature(*sig)
	must(err)
	pub, err := readPublic(*key)
	must(err)
	m, err := verifyManifest(b, s, pub, alpha.VerifyOptions{MinSequence: *min, RaceVersion: *rv, RelayVersion: *lv, Now: time.Now().UTC()})
	must(cliError(err))
	fmt.Printf("verified alpha channel sequence %d: race_engineer %s, relay %s\n", m.ReleaseSequence, m.RaceEngineer.Version, m.Relay.Version)
}
func publishCmd(args []string) {
	fs := flag.NewFlagSet("publish", flag.ExitOnError)
	mf := fs.String("manifest", "", "manifest path")
	key := fs.String("private-key", "", "external Ed25519 private key")
	out := fs.String("output-dir", "", "empty target directory")
	dry := fs.Bool("dry-run", false, "validate and sign without writing")
	fs.Parse(args)
	if *mf == "" || *key == "" {
		die("--manifest and --private-key are required")
	}
	if !*dry && *out == "" {
		die("--output-dir is required unless --dry-run")
	}
	b, err := readManifest(*mf)
	must(err)
	priv, err := readPrivate(*key)
	must(err)
	_, err = alpha.ParseManifest(b, time.Now().UTC())
	must(cliError(err))
	s := ed25519.Sign(priv, alpha.SignedPayload(b))
	if *dry {
		fmt.Println("dry run: manifest validates and detached signature was created in memory")
		return
	}
	must(writePair(*out, b, []byte(base64.StdEncoding.EncodeToString(s)+"\n")))
	fmt.Println("wrote unsigned-release staging files; publish only after immutable assets are independently verified")
}

// verifyManifest is intentionally only a CLI adapter; all policy is in alpha.
func verifyManifest(b, sig []byte, pub ed25519.PublicKey, o alpha.VerifyOptions) (alpha.Manifest, error) {
	return alpha.VerifyTrustTransition(b, sig, pub, o)
}
func readManifest(name string) ([]byte, error) {
	b, err := readFileBounded(name, alpha.MaxManifestBytes)
	if err != nil && strings.HasPrefix(err.Error(), "file exceeds ") {
		return nil, alpha.ErrManifestTooLarge
	}
	return b, err
}
func readSignature(name string) ([]byte, error) {
	b, err := readFileBounded(name, alpha.MaxSignatureBytes)
	if err != nil {
		return nil, err
	}
	b, err = decodeKeyBytes(b)
	if err != nil {
		return nil, err
	}
	if len(b) != ed25519.SignatureSize {
		return nil, errors.New("signature must be raw, base64, or hex Ed25519 bytes")
	}
	return b, nil
}
func readPublic(p string) (ed25519.PublicKey, error) {
	b, e := readKey(p)
	if e != nil {
		return nil, e
	}
	if len(b) == ed25519.PublicKeySize {
		return ed25519.PublicKey(b), nil
	}
	k, e := x509.ParsePKIXPublicKey(b)
	if e == nil {
		if p, ok := k.(ed25519.PublicKey); ok {
			return p, nil
		}
	}
	return nil, errors.New("public key must be raw base64/hex or Ed25519 PKIX PEM/DER")
}
func readPrivate(p string) (ed25519.PrivateKey, error) {
	b, e := readKey(p)
	if e != nil {
		return nil, e
	}
	if len(b) == ed25519.PrivateKeySize {
		return ed25519.PrivateKey(b), nil
	}
	k, e := x509.ParsePKCS8PrivateKey(b)
	if e == nil {
		if p, ok := k.(ed25519.PrivateKey); ok {
			return p, nil
		}
	}
	return nil, errors.New("private key must be raw base64/hex or Ed25519 PKCS8 PEM/DER")
}
func readKey(p string) ([]byte, error) {
	b, e := os.ReadFile(p)
	if e != nil {
		return nil, e
	}
	return decodeKeyBytes(b)
}
func decodeKeyBytes(b []byte) ([]byte, error) {
	s := strings.TrimSpace(string(b))
	if v, e := hex.DecodeString(s); e == nil {
		return v, nil
	}
	if v, e := base64.StdEncoding.DecodeString(s); e == nil {
		return v, nil
	}
	if block, _ := pem.Decode(b); block != nil {
		return block.Bytes, nil
	}
	return b, nil
}
func readFileBounded(name string, limit int64) ([]byte, error) {
	f, err := os.Open(name)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	b, err := io.ReadAll(io.LimitReader(f, limit+1))
	if err != nil {
		return nil, err
	}
	if int64(len(b)) > limit {
		return nil, fmt.Errorf("file exceeds %d bytes", limit)
	}
	return b, nil
}
func writePair(dir string, manifestBytes, signature []byte) error {
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	manifestPath := filepath.Join(dir, "alpha.json")
	signaturePath := filepath.Join(dir, "alpha.json.sig")
	if err := createOnce(manifestPath, manifestBytes); err != nil {
		return err
	}
	if err := createOnce(signaturePath, signature); err != nil {
		if cleanupErr := os.Remove(manifestPath); cleanupErr != nil {
			return fmt.Errorf("signature creation failed; manifest cleanup failed (%v): %w", cleanupErr, err)
		}
		return fmt.Errorf("signature creation failed; manifest removed: %w", err)
	}
	return nil
}
func createOnce(name string, contents []byte) error {
	f, err := os.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0644)
	if err != nil {
		return fmt.Errorf("refusing overwrite %s: %w", name, err)
	}
	if _, err := f.Write(contents); err != nil {
		f.Close()
		os.Remove(name)
		return err
	}
	if err := f.Close(); err != nil {
		os.Remove(name)
		return err
	}
	return nil
}
func must(e error) {
	if e != nil {
		die(e.Error())
	}
}
func cliError(err error) error {
	if err == nil {
		return nil
	}
	s := err.Error()
	if key, ok := strings.CutPrefix(s, "unknown or non-canonical JSON key "); ok {
		return fmt.Errorf("json: unknown field %s", key)
	}
	s = strings.NewReplacer(
		"alpha.Manifest", "main.manifest",
		"alpha.KeyRotation", "main.keyRotation",
		"alpha.Release", "main.release",
		"Manifest.", "manifest.",
		"KeyRotation.", "keyRotation.",
		"Release.", "release.",
	).Replace(s)
	return errors.New(s)
}
func die(s string) { fmt.Fprintln(os.Stderr, "alpha-channel:", s); os.Exit(1) }
