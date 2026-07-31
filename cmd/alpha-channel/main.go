package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	maxManifestBytes = 64 << 10
	domain           = "TeamManager Alpha Channel v1\x00"
	forgejoHost      = "forgejo.g-grp.com"
	forgejoOwner     = "Max"
)

var versionRE = regexp.MustCompile(`^0\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*$`)
var hex40RE = regexp.MustCompile(`^[0-9a-f]{40}$`)
var shaRE = regexp.MustCompile(`^[0-9a-f]{64}$`)
var fileRE = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*\.exe$`)

type manifest struct {
	Schema          int         `json:"schema"`
	Channel         string      `json:"channel"`
	KeyID           string      `json:"key_id"`
	KeyRotation     keyRotation `json:"key_rotation"`
	GeneratedAt     string      `json:"generated_at"`
	ExpiresAt       string      `json:"expires_at"`
	ReleaseSequence uint64      `json:"release_sequence"`
	RaceEngineer    release     `json:"race_engineer"`
	Relay           release     `json:"relay"`
}
type keyRotation struct {
	Status    string `json:"status"`
	NotBefore string `json:"not_before"`
	NotAfter  string `json:"not_after"`
}
type release struct {
	Product      string `json:"product"`
	Platform     string `json:"platform"`
	Architecture string `json:"architecture"`
	Version      string `json:"version"`
	Tag          string `json:"tag"`
	Commit       string `json:"commit"`
	Owner        string `json:"owner"`
	Repository   string `json:"repository"`
	URL          string `json:"url"`
	Filename     string `json:"filename"`
	Size         int64  `json:"size"`
	SHA256       string `json:"sha256"`
}

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
	b, err := os.ReadFile(*mf)
	must(err)
	s, err := readSignature(*sig)
	must(err)
	pub, err := readPublic(*key)
	must(err)
	m, err := verify(b, s, pub, verifyOptions{MinSequence: *min, RaceVersion: *rv, RelayVersion: *lv, Now: time.Now().UTC()})
	must(err)
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
	b, err := os.ReadFile(*mf)
	must(err)
	priv, err := readPrivate(*key)
	must(err)
	m, err := parseManifest(b, time.Now().UTC())
	must(err)
	_ = m
	s := ed25519.Sign(priv, signedPayload(b))
	if *dry {
		fmt.Println("dry run: manifest validates and detached signature was created in memory")
		return
	}
	if err := os.MkdirAll(*out, 0755); err != nil {
		die(err.Error())
	}
	for _, n := range []string{"alpha.json", "alpha.json.sig"} {
		if _, err := os.Stat(path.Join(*out, n)); err == nil {
			die("refusing overwrite: " + path.Join(*out, n))
		} else if !errors.Is(err, os.ErrNotExist) {
			die(err.Error())
		}
	}
	must(os.WriteFile(path.Join(*out, "alpha.json"), b, 0644))
	must(os.WriteFile(path.Join(*out, "alpha.json.sig"), []byte(base64.StdEncoding.EncodeToString(s)+"\n"), 0644))
	fmt.Println("wrote unsigned-release staging files; publish only after immutable assets are independently verified")
}

type verifyOptions struct {
	MinSequence               uint64
	RaceVersion, RelayVersion string
	Now                       time.Time
}

func verify(b, s []byte, pub ed25519.PublicKey, o verifyOptions) (manifest, error) {
	if !ed25519.Verify(pub, signedPayload(b), s) {
		return manifest{}, errors.New("invalid detached signature")
	}
	m, err := parseManifest(b, o.Now)
	if err != nil {
		return manifest{}, err
	}
	if m.ReleaseSequence <= o.MinSequence {
		return manifest{}, errors.New("release_sequence is not newer")
	}
	if o.RaceVersion != "" && compareVersion(m.RaceEngineer.Version, o.RaceVersion) <= 0 {
		return manifest{}, errors.New("race_engineer version is not newer")
	}
	if o.RelayVersion != "" && compareVersion(m.Relay.Version, o.RelayVersion) <= 0 {
		return manifest{}, errors.New("relay version is not newer")
	}
	return m, nil
}
func parseManifest(b []byte, now time.Time) (manifest, error) {
	if len(b) > maxManifestBytes {
		return manifest{}, errors.New("manifest exceeds 64 KiB")
	}
	if !utf8.Valid(b) {
		return manifest{}, errors.New("manifest is not valid UTF-8")
	}
	if err := rejectDuplicates(b); err != nil {
		return manifest{}, err
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	var m manifest
	if err := dec.Decode(&m); err != nil {
		return manifest{}, err
	}
	if dec.Decode(&struct{}{}) != io.EOF {
		return manifest{}, errors.New("trailing JSON data")
	}
	if err := validate(m, now); err != nil {
		return manifest{}, err
	}
	return m, nil
}
func rejectDuplicates(b []byte) error {
	d := json.NewDecoder(bytes.NewReader(b))
	var value func() error
	value = func() error {
		t, e := d.Token()
		if e != nil {
			return e
		}
		switch x := t.(type) {
		case json.Delim:
			if x == '{' {
				seen := map[string]bool{}
				for d.More() {
					k, e := d.Token()
					if e != nil {
						return e
					}
					ks := k.(string)
					if seen[ks] {
						return fmt.Errorf("duplicate JSON key %q", ks)
					}
					seen[ks] = true
					if e := value(); e != nil {
						return e
					}
				}
				_, e = d.Token()
				return e
			}
			if x == '[' {
				for d.More() {
					if e := value(); e != nil {
						return e
					}
				}
				_, e = d.Token()
				return e
			}
		}
		return nil
	}
	if err := value(); err != nil {
		return err
	}
	if d.More() {
		return errors.New("trailing JSON data")
	}
	return nil
}
func validate(m manifest, now time.Time) error {
	if m.Schema != 1 || m.Channel != "alpha" || m.KeyID != "alpha-1" || m.ReleaseSequence == 0 {
		return errors.New("invalid schema, channel, key_id, or release_sequence")
	}
	if m.KeyRotation.Status != "active" || m.KeyRotation.NotBefore == "" || m.KeyRotation.NotAfter == "" {
		return errors.New("invalid key_rotation metadata")
	}
	g, e := utc(m.GeneratedAt)
	if e != nil {
		return e
	}
	x, e := utc(m.ExpiresAt)
	if e != nil {
		return e
	}
	nb, e := utc(m.KeyRotation.NotBefore)
	if e != nil {
		return e
	}
	na, e := utc(m.KeyRotation.NotAfter)
	if e != nil {
		return e
	}
	if g.After(now.Add(5*time.Minute)) || !x.After(now) || !x.After(g) || na.Before(x) || nb.After(g) {
		return errors.New("invalid publication, expiry, or rotation window")
	}
	if err := validateRelease(m.RaceEngineer, "race_engineer", "race-engineer-go"); err != nil {
		return err
	}
	return validateRelease(m.Relay, "relay", "teammanager-relay")
}
func utc(s string) (time.Time, error) {
	t, e := time.Parse(time.RFC3339, s)
	if e != nil || t.Location() != time.UTC || !strings.HasSuffix(s, "Z") {
		return time.Time{}, errors.New("timestamps must be RFC3339 UTC")
	}
	return t, nil
}
func validateRelease(r release, product, repo string) error {
	if r.Product != product || r.Platform != "windows" || r.Architecture != "amd64" || !versionRE.MatchString(r.Version) || r.Tag == "" || !hex40RE.MatchString(r.Commit) || r.Owner != forgejoOwner || r.Repository != repo || !fileRE.MatchString(r.Filename) || r.Size <= 0 || r.Size > 8<<30 || !shaRE.MatchString(r.SHA256) {
		return fmt.Errorf("invalid %s release fields", product)
	}
	want := "https://" + forgejoHost + "/" + forgejoOwner + "/" + repo + "/releases/download/" + r.Tag + "/" + r.Filename
	if r.URL != want {
		return fmt.Errorf("invalid %s asset URL", product)
	}
	return nil
}
func compareVersion(a, b string) int {
	pa := strings.FieldsFunc(a, func(r rune) bool { return r == '.' || r == '-' })
	pb := strings.FieldsFunc(b, func(r rune) bool { return r == '.' || r == '-' })
	for _, i := range []int{0, 1, 2, 4} {
		ai, _ := strconv.Atoi(pa[i])
		bi, _ := strconv.Atoi(pb[i])
		if ai < bi {
			return -1
		}
		if ai > bi {
			return 1
		}
	}
	return 0
}
func signedPayload(b []byte) []byte { return append([]byte(domain), b...) }
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
func readSignature(p string) ([]byte, error) {
	b, err := readKey(p)
	if err != nil {
		return nil, err
	}
	if len(b) != ed25519.SignatureSize {
		return nil, errors.New("signature must be raw, base64, or hex Ed25519 bytes")
	}
	return b, nil
}
func must(e error) {
	if e != nil {
		die(e.Error())
	}
}
func die(s string) { fmt.Fprintln(os.Stderr, "alpha-channel:", s); os.Exit(1) }
