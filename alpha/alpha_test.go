package alpha_test

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"forgejo.g-grp.com/Max/teammanager-models/alpha"
)

func valid(t time.Time) []byte {
	m := alpha.Manifest{Schema: 1, Channel: "alpha", KeyID: "alpha-1", KeyRotation: alpha.KeyRotation{Status: "active", NotBefore: t.Add(-time.Hour).Format(time.RFC3339), NotAfter: t.Add(24 * time.Hour).Format(time.RFC3339)}, GeneratedAt: t.Add(-time.Minute).Format(time.RFC3339), ExpiresAt: t.Add(time.Hour).Format(time.RFC3339), ReleaseSequence: 7, AuthenticodePolicy: "not-required", RaceEngineer: release("race_engineer", "race-engineer-go", "RaceSetup.exe"), Relay: release("relay", "teammanager-relay", "RelaySetup.exe")}
	b, _ := json.Marshal(m)
	return b
}
func release(product, repo, name string) alpha.Release {
	v := "0.1.0-alpha.7"
	return alpha.Release{Product: product, Platform: "windows", Architecture: "amd64", Version: v, Tag: "v" + v, Commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", Owner: "Max", Repository: repo, URL: "https://forgejo.g-grp.com/Max/" + repo + "/releases/download/v" + v + "/" + name, Filename: name, Size: 1, SHA256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
}
func TestTrustTransitionNegativeGates(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	b := valid(now)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sig := ed25519.Sign(priv, alpha.SignedPayload(b))
	if _, err := alpha.VerifyTrustTransition(b, sig, pub, alpha.VerifyOptions{Now: now, MinSequence: 6, RaceVersion: "0.1.0-alpha.6", RelayVersion: "0.1.0-alpha.6"}); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name string
		b, s []byte
		o    alpha.VerifyOptions
	}{{"altered bytes", append(b, ' '), sig, alpha.VerifyOptions{Now: now}}, {"replay", b, sig, alpha.VerifyOptions{Now: now, MinSequence: 7}}, {"downgrade", b, sig, alpha.VerifyOptions{Now: now, RaceVersion: "0.1.0-alpha.7"}}, {"duplicate", []byte(`{"schema":1,"schema":1}`), sig, alpha.VerifyOptions{Now: now}}} {
		t.Run(tc.name, func(t *testing.T) {
			if _, err := alpha.VerifyTrustTransition(tc.b, tc.s, pub, tc.o); err == nil {
				t.Fatal("accepted invalid trust transition")
			}
		})
	}
}
func TestParseNegativeGates(t *testing.T) {
	now := time.Now().UTC()
	base := valid(now)
	var nullField map[string]any
	if err := json.Unmarshal(base, &nullField); err != nil {
		t.Fatal(err)
	}
	nullField["key_rotation"] = nil
	nullKeyRotation, err := json.Marshal(nullField)
	if err != nil {
		t.Fatal(err)
	}
	for _, b := range [][]byte{make([]byte, alpha.MaxManifestBytes+1), {0xff}, []byte(`{"schema":1,"unknown":true}`), []byte(`null`), []byte(`[]`), []byte(strings.Replace(string(base), `"schema":1`, `"schema":"1"`, 1)), nullKeyRotation} {
		if _, err := alpha.ParseManifest(b, now); err == nil {
			t.Fatal("accepted invalid manifest")
		}
	}
}

func TestAllReleaseAndTimeGatesRemainClosed(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	mutations := []func(*alpha.Manifest){
		func(m *alpha.Manifest) { m.RaceEngineer.Product = "relay" },
		func(m *alpha.Manifest) { m.RaceEngineer.Platform = "linux" },
		func(m *alpha.Manifest) { m.RaceEngineer.Architecture = "arm64" },
		func(m *alpha.Manifest) { m.RaceEngineer.Owner = "Other" },
		func(m *alpha.Manifest) { m.RaceEngineer.Repository = "other" },
		func(m *alpha.Manifest) { m.RaceEngineer.URL += "?query" },
		func(m *alpha.Manifest) { m.RaceEngineer.URL += "#fragment" },
		func(m *alpha.Manifest) {
			m.RaceEngineer.URL = "https://forgejo.g-grp.com/Max/race-engineer-go/releases/download/v0.1.0-alpha.7/../RaceSetup.exe"
		},
		func(m *alpha.Manifest) {
			m.RaceEngineer.URL = "https://forgejo.g-grp.com/Max/race-engineer-go/releases/download/v0.1.0-alpha.7/%52aceSetup.exe"
		},
		func(m *alpha.Manifest) { m.RaceEngineer.Tag = "bad" },
		func(m *alpha.Manifest) { m.RaceEngineer.Commit = "ABC" },
		func(m *alpha.Manifest) { m.RaceEngineer.Version = "1.0.0" },
		func(m *alpha.Manifest) { m.RaceEngineer.Size = 0 },
		func(m *alpha.Manifest) { m.RaceEngineer.SHA256 = "ABC" },
		func(m *alpha.Manifest) { m.AuthenticodePolicy = "optional" },
		func(m *alpha.Manifest) { m.ExpiresAt = now.Add(-time.Second).Format(time.RFC3339) },
		func(m *alpha.Manifest) { m.GeneratedAt = now.Add(6 * time.Minute).Format(time.RFC3339) },
	}
	for _, mutate := range mutations {
		var m alpha.Manifest
		if err := json.Unmarshal(valid(now), &m); err != nil {
			t.Fatal(err)
		}
		mutate(&m)
		b, err := json.Marshal(m)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := alpha.ParseManifest(b, now); err == nil {
			t.Fatal("accepted closed-gate mutation")
		}
	}
	for _, v := range []string{"", "0.1", "0.1.0", "0.1.0-alpha.0", "0.1.0-alpha.x", "0.18446744073709551616.0-alpha.1"} {
		if _, err := alpha.CompareVersion(v, "0.1.0-alpha.1"); err == nil {
			t.Fatalf("accepted invalid version %q", v)
		}
	}
}
