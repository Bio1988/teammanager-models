package alpha_test

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"errors"
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

func TestCaseFoldCollisionsAreRejectedBeforeStructDecoding(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range caseCollisionVectors(t, now) {
		t.Run(tc, func(t *testing.T) {
			b := collisionVector(t, now, tc)
			sig := ed25519.Sign(priv, alpha.SignedPayload(b))
			if _, err := alpha.VerifyTrustTransition(b, sig, pub, alpha.VerifyOptions{Now: now}); err == nil {
				t.Fatal("accepted signed case-fold collision")
			}
		})
	}
}

func TestSignedExactDuplicateKeysReachClosedJSONGate(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	base := valid(now)
	vectors := map[string][]byte{
		"top-level":         append(append([]byte{}, base[:len(base)-1]...), []byte(`,"schema":1}`)...),
		"key_rotation":      []byte(strings.Replace(string(base), `"status":"active"`, `"status":"active","status":"active"`, 1)),
		"release":           []byte(strings.Replace(string(base), `"product":"race_engineer"`, `"product":"race_engineer","product":"race_engineer"`, 1)),
		"scalar object":     []byte(strings.Replace(string(base), `"schema":1`, `"schema":{"x":1,"x":1}`, 1)),
		"root array object": []byte(`[{"x":1,"x":1}]`),
	}
	for name, b := range vectors {
		t.Run(name, func(t *testing.T) {
			sig := ed25519.Sign(priv, alpha.SignedPayload(b))
			if _, err := alpha.VerifyTrustTransition(b, sig, pub, alpha.VerifyOptions{Now: now}); err == nil || !strings.Contains(err.Error(), "duplicate JSON key") {
				t.Fatalf("exact duplicate did not reach closed JSON gate: %v", err)
			}
		})
	}
}

func TestScalarContainersReachTypeGateWithoutAcceptance(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	var m map[string]any
	if err := json.Unmarshal(valid(now), &m); err != nil {
		t.Fatal(err)
	}
	m["schema"] = map[string]any{"unknown": true}
	b, err := json.Marshal(m)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := alpha.ParseManifest(b, now); err == nil {
		t.Fatal("scalar object was accepted")
	}
}

func caseCollisionVectors(t *testing.T, now time.Time) []string {
	t.Helper()
	var root map[string]any
	if err := json.Unmarshal(valid(now), &root); err != nil {
		t.Fatal(err)
	}
	keys := make([]string, 0, len(root)+3+24)
	for key := range root {
		keys = append(keys, "root."+key)
	}
	for _, object := range []string{"key_rotation", "race_engineer", "relay"} {
		child := root[object].(map[string]any)
		for key := range child {
			keys = append(keys, object+"."+key)
		}
	}
	return keys
}

func collisionVector(t *testing.T, now time.Time, path string) []byte {
	t.Helper()
	var root map[string]any
	if err := json.Unmarshal(valid(now), &root); err != nil {
		t.Fatal(err)
	}
	parts := strings.Split(path, ".")
	object := root
	key := parts[len(parts)-1]
	if parts[0] != "root" {
		object = root[parts[0]].(map[string]any)
	}
	object[strings.ToUpper(key)] = object[key]
	b, err := json.Marshal(root)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func TestVerifyLengthGatesAreBoundedAndDoNotPanic(t *testing.T) {
	now := time.Now().UTC()
	b := valid(now)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sig := ed25519.Sign(priv, alpha.SignedPayload(b))
	cases := []struct {
		name   string
		b, sig []byte
		pub    ed25519.PublicKey
		want   error
	}{
		{"oversized manifest", make([]byte, alpha.MaxManifestBytes+1), sig, pub, alpha.ErrManifestTooLarge},
		{"nil public key", b, sig, nil, alpha.ErrInvalidPublicKey},
		{"short public key", b, sig, ed25519.PublicKey(make([]byte, ed25519.PublicKeySize-1)), alpha.ErrInvalidPublicKey},
		{"long public key", b, sig, ed25519.PublicKey(make([]byte, ed25519.PublicKeySize+1)), alpha.ErrInvalidPublicKey},
		{"nil signature", b, nil, pub, alpha.ErrInvalidSignature},
		{"short signature", b, make([]byte, ed25519.SignatureSize-1), pub, alpha.ErrInvalidSignature},
		{"long signature", b, make([]byte, ed25519.SignatureSize+1), pub, alpha.ErrInvalidSignature},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			defer func() {
				if got := recover(); got != nil {
					t.Fatalf("panic: %v", got)
				}
			}()
			_, err := alpha.VerifyTrustTransition(tc.b, tc.sig, tc.pub, alpha.VerifyOptions{Now: now})
			if !errors.Is(err, tc.want) {
				t.Fatalf("got %v, want %v", err, tc.want)
			}
		})
	}
}
