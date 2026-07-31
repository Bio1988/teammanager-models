package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func valid(now time.Time) []byte {
	m := manifest{Schema: 1, Channel: "alpha", KeyID: "alpha-1", KeyRotation: keyRotation{"active", now.Add(-time.Hour).Format(time.RFC3339), now.Add(24 * time.Hour).Format(time.RFC3339)}, GeneratedAt: now.Add(-time.Minute).Format(time.RFC3339), ExpiresAt: now.Add(time.Hour).Format(time.RFC3339), ReleaseSequence: 7, RaceEngineer: releaseFor("race_engineer", "race-engineer-go", "RaceSetup.exe"), Relay: releaseFor("relay", "teammanager-relay", "RelaySetup.exe")}
	b, _ := json.Marshal(m)
	return b
}
func releaseFor(product, repo, file string) release {
	v := "0.1.0-alpha.7"
	tag := "v" + v
	return release{Product: product, Platform: "windows", Architecture: "amd64", Version: v, Tag: tag, Commit: strings.Repeat("a", 40), Owner: "Max", Repository: repo, URL: "https://forgejo.g-grp.com/Max/" + repo + "/releases/download/" + tag + "/" + file, Filename: file, Size: 1, SHA256: strings.Repeat("b", 64)}
}
func signed(t *testing.T, b []byte) ([]byte, ed25519.PublicKey) {
	t.Helper()
	pub, priv, e := ed25519.GenerateKey(rand.Reader)
	if e != nil {
		t.Fatal(e)
	}
	return ed25519.Sign(priv, signedPayload(b)), pub
}
func TestPositiveVector(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	b := valid(now)
	s, p := signed(t, b)
	if _, e := verify(b, s, p, verifyOptions{Now: now, MinSequence: 6, RaceVersion: "0.1.0-alpha.6", RelayVersion: "0.1.0-alpha.6"}); e != nil {
		t.Fatal(e)
	}
}
func TestRejectsSignatureAndExactBytes(t *testing.T) {
	now := time.Now().UTC()
	b := valid(now)
	s, p := signed(t, b)
	if _, e := verify(b, s, p, verifyOptions{Now: now}); e != nil {
		t.Fatal(e)
	}
	if _, e := verify(append(b, ' '), s, p, verifyOptions{Now: now}); e == nil {
		t.Fatal("accepted altered bytes")
	}
	s[0] ^= 1
	if _, e := verify(b, s, p, verifyOptions{Now: now}); e == nil {
		t.Fatal("accepted altered signature")
	}
}
func TestClosedDuplicateAndUnknownJSON(t *testing.T) {
	now := time.Now().UTC()
	b := valid(now)
	if _, e := parseManifest([]byte(`{"schema":1,"schema":1}`), now); e == nil {
		t.Fatal("duplicate accepted")
	}
	if _, e := parseManifest([]byte(strings.Replace(string(b), `"status":"active"`, `"status":"active","status":"active"`, 1)), now); e == nil {
		t.Fatal("nested duplicate accepted")
	}
	if _, e := parseManifest(append(b[:len(b)-1], []byte(`,"unknown":1}`)...), now); e == nil {
		t.Fatal("unknown accepted")
	}
}
func TestReleaseFieldVectors(t *testing.T) {
	now := time.Now().UTC()
	cases := []struct {
		name string
		mut  func(*manifest)
	}{{"product", func(m *manifest) { m.RaceEngineer.Product = "relay" }}, {"platform", func(m *manifest) { m.RaceEngineer.Platform = "linux" }}, {"arch", func(m *manifest) { m.RaceEngineer.Architecture = "arm64" }}, {"owner", func(m *manifest) { m.RaceEngineer.Owner = "Other" }}, {"repo", func(m *manifest) { m.RaceEngineer.Repository = "other" }}, {"url", func(m *manifest) {
		m.RaceEngineer.URL = "https://forgejo.g-grp.com/Max/race-engineer-go/releases/download/v0.1.0-alpha.7/RaceSetup.exe?q=x"
	}}, {"tag", func(m *manifest) { m.RaceEngineer.Tag = "bad" }}, {"commit", func(m *manifest) { m.RaceEngineer.Commit = "ABC" }}, {"version", func(m *manifest) { m.RaceEngineer.Version = "1.0.0" }}, {"size", func(m *manifest) { m.RaceEngineer.Size = 0 }}, {"hash", func(m *manifest) { m.RaceEngineer.SHA256 = "ABC" }}}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var m manifest
			json.Unmarshal(valid(now), &m)
			tc.mut(&m)
			b, _ := json.Marshal(m)
			if _, e := parseManifest(b, now); e == nil {
				t.Fatal("accepted invalid " + tc.name)
			}
		})
	}
}
func TestExpiryFutureReplayDowngradeAndRedirect(t *testing.T) {
	now := time.Now().UTC()
	var m manifest
	json.Unmarshal(valid(now), &m)
	m.ExpiresAt = now.Add(-time.Second).Format(time.RFC3339)
	b, _ := json.Marshal(m)
	if _, e := parseManifest(b, now); e == nil {
		t.Fatal("expired")
	}
	json.Unmarshal(valid(now), &m)
	m.GeneratedAt = now.Add(6 * time.Minute).Format(time.RFC3339)
	b, _ = json.Marshal(m)
	if _, e := parseManifest(b, now); e == nil {
		t.Fatal("future")
	}
	b = valid(now)
	s, p := signed(t, b)
	if _, e := verify(b, s, p, verifyOptions{Now: now, MinSequence: 7}); e == nil {
		t.Fatal("replay")
	}
	if _, e := verify(b, s, p, verifyOptions{Now: now, RaceVersion: "0.1.0-alpha.7"}); e == nil {
		t.Fatal("downgrade")
	}
	json.Unmarshal(valid(now), &m)
	m.Relay.URL = "https://forgejo.g-grp.com/redirect"
	b, _ = json.Marshal(m)
	if _, e := parseManifest(b, now); e == nil {
		t.Fatal("redirect URL accepted")
	}
}
