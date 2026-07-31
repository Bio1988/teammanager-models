// Package alpha validates the signed TeamManager Alpha application channel.
// It is deliberately side-effect free: callers supply all bytes and retain
// their own accepted trust record.
package alpha

import (
	"bytes"
	"crypto/ed25519"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	MaxManifestBytes  = 64 << 10
	MaxSignatureBytes = 4 << 10
	domain            = "TeamManager Alpha Channel v1\x00"
	forgejoHost       = "forgejo.g-grp.com"
	forgejoOwner      = "Max"
)

var versionRE = regexp.MustCompile(`^0\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*$`)
var versionPartsRE = regexp.MustCompile(`^0\.([0-9]+)\.([0-9]+)-alpha\.([1-9][0-9]*)$`)
var hex40RE = regexp.MustCompile(`^[0-9a-f]{40}$`)
var shaRE = regexp.MustCompile(`^[0-9a-f]{64}$`)
var fileRE = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*\.exe$`)

type Manifest struct {
	Schema             int         `json:"schema"`
	Channel            string      `json:"channel"`
	KeyID              string      `json:"key_id"`
	KeyRotation        KeyRotation `json:"key_rotation"`
	GeneratedAt        string      `json:"generated_at"`
	ExpiresAt          string      `json:"expires_at"`
	ReleaseSequence    uint64      `json:"release_sequence"`
	AuthenticodePolicy string      `json:"authenticode_policy"`
	RaceEngineer       Release     `json:"race_engineer"`
	Relay              Release     `json:"relay"`
}
type KeyRotation struct {
	Status    string `json:"status"`
	NotBefore string `json:"not_before"`
	NotAfter  string `json:"not_after"`
}
type Release struct {
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

type VerifyOptions struct {
	MinSequence  uint64
	RaceVersion  string
	RelayVersion string
	Now          time.Time
}

// SignedPayload applies the non-ambiguous application-channel domain.
func SignedPayload(manifest []byte) []byte { return append([]byte(domain), manifest...) }

// ParseManifest enforces the exact byte, UTF-8, closed JSON, and field rules.
func ParseManifest(b []byte, now time.Time) (Manifest, error) {
	if len(b) > MaxManifestBytes {
		return Manifest{}, errors.New("manifest exceeds 64 KiB")
	}
	if !utf8.Valid(b) {
		return Manifest{}, errors.New("manifest is not valid UTF-8")
	}
	if err := rejectDuplicates(b); err != nil {
		return Manifest{}, err
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.DisallowUnknownFields()
	var m Manifest
	if err := dec.Decode(&m); err != nil {
		return Manifest{}, err
	}
	if dec.Decode(&struct{}{}) != io.EOF {
		return Manifest{}, errors.New("trailing JSON data")
	}
	if err := ValidateManifest(m, now); err != nil {
		return Manifest{}, err
	}
	return m, nil
}

func ValidateManifest(m Manifest, now time.Time) error {
	if m.Schema != 1 || m.Channel != "alpha" || m.KeyID != "alpha-1" || m.ReleaseSequence == 0 || (m.AuthenticodePolicy != "not-required" && m.AuthenticodePolicy != "required") {
		return errors.New("invalid schema, channel, key_id, release_sequence, or authenticode_policy")
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

// VerifyTrustTransition verifies a signature and rejects replay and downgrade
// against the caller-owned prior accepted sequence and installed versions.
func VerifyTrustTransition(b, sig []byte, pub ed25519.PublicKey, o VerifyOptions) (Manifest, error) {
	if !ed25519.Verify(pub, SignedPayload(b), sig) {
		return Manifest{}, errors.New("invalid detached signature")
	}
	m, err := ParseManifest(b, o.Now)
	if err != nil {
		return Manifest{}, err
	}
	if m.ReleaseSequence <= o.MinSequence {
		return Manifest{}, errors.New("release_sequence is not newer")
	}
	if o.RaceVersion != "" {
		cmp, err := CompareVersion(m.RaceEngineer.Version, o.RaceVersion)
		if err != nil {
			return Manifest{}, fmt.Errorf("invalid installed race_engineer version: %w", err)
		}
		if cmp <= 0 {
			return Manifest{}, errors.New("race_engineer version is not newer")
		}
	}
	if o.RelayVersion != "" {
		cmp, err := CompareVersion(m.Relay.Version, o.RelayVersion)
		if err != nil {
			return Manifest{}, fmt.Errorf("invalid installed relay version: %w", err)
		}
		if cmp <= 0 {
			return Manifest{}, errors.New("relay version is not newer")
		}
	}
	return m, nil
}

func CompareVersion(a, b string) (int, error) {
	pa, err := parseVersion(a)
	if err != nil {
		return 0, err
	}
	pb, err := parseVersion(b)
	if err != nil {
		return 0, err
	}
	for i := range pa {
		if pa[i] < pb[i] {
			return -1, nil
		}
		if pa[i] > pb[i] {
			return 1, nil
		}
	}
	return 0, nil
}
func parseVersion(v string) ([3]uint64, error) {
	m := versionPartsRE.FindStringSubmatch(v)
	if m == nil {
		return [3]uint64{}, errors.New("must be 0.x.y-alpha.N")
	}
	var out [3]uint64
	for i := range out {
		n, err := strconv.ParseUint(m[i+1], 10, 64)
		if err != nil {
			return [3]uint64{}, errors.New("numeric component overflows")
		}
		out[i] = n
	}
	return out, nil
}
func utc(s string) (time.Time, error) {
	t, e := time.Parse(time.RFC3339, s)
	if e != nil || t.Location() != time.UTC || !strings.HasSuffix(s, "Z") {
		return time.Time{}, errors.New("timestamps must be RFC3339 UTC")
	}
	return t, nil
}
func validateRelease(r Release, product, repo string) error {
	if r.Product != product || r.Platform != "windows" || r.Architecture != "amd64" || !versionRE.MatchString(r.Version) || r.Tag != "v"+r.Version || !hex40RE.MatchString(r.Commit) || r.Owner != forgejoOwner || r.Repository != repo || !fileRE.MatchString(r.Filename) || r.Size <= 0 || r.Size > 8<<30 || !shaRE.MatchString(r.SHA256) {
		return fmt.Errorf("invalid %s release fields", product)
	}
	if _, err := parseVersion(r.Version); err != nil {
		return fmt.Errorf("invalid %s version: %w", product, err)
	}
	want := "https://" + forgejoHost + "/" + forgejoOwner + "/" + repo + "/releases/download/" + r.Tag + "/" + r.Filename
	if r.URL != want {
		return fmt.Errorf("invalid %s asset URL", product)
	}
	return nil
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
