package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"forgejo.g-grp.com/Max/teammanager-models/alpha"
)

func manifestBytes(now time.Time) []byte {
	m := alpha.Manifest{Schema: 1, Channel: "alpha", KeyID: "alpha-1", KeyRotation: alpha.KeyRotation{Status: "active", NotBefore: now.Add(-time.Hour).Format(time.RFC3339), NotAfter: now.Add(24 * time.Hour).Format(time.RFC3339)}, GeneratedAt: now.Add(-time.Minute).Format(time.RFC3339), ExpiresAt: now.Add(time.Hour).Format(time.RFC3339), ReleaseSequence: 7, AuthenticodePolicy: "not-required", RaceEngineer: testRelease("race_engineer", "race-engineer-go", "RaceSetup.exe"), Relay: testRelease("relay", "teammanager-relay", "RelaySetup.exe")}
	b, _ := json.Marshal(m)
	return b
}
func testRelease(product, repo, filename string) alpha.Release {
	v := "0.1.0-alpha.7"
	return alpha.Release{Product: product, Platform: "windows", Architecture: "amd64", Version: v, Tag: "v" + v, Commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", Owner: "Max", Repository: repo, URL: "https://forgejo.g-grp.com/Max/" + repo + "/releases/download/v" + v + "/" + filename, Filename: filename, Size: 1, SHA256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
}
func TestCLILibraryParityAndNegativeGates(t *testing.T) {
	now := time.Date(2026, 7, 31, 12, 0, 0, 0, time.UTC)
	b := manifestBytes(now)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sig := ed25519.Sign(priv, alpha.SignedPayload(b))
	o := alpha.VerifyOptions{Now: now, MinSequence: 6}
	want, wantErr := alpha.VerifyTrustTransition(b, sig, pub, o)
	got, gotErr := verifyManifest(b, sig, pub, o)
	if (wantErr != nil) != (gotErr != nil) || got != want {
		t.Fatalf("library/CLI disagreement: library=%v cli=%v", wantErr, gotErr)
	}
	for _, tc := range [][]byte{append(b, ' '), []byte(`{"schema":1,"schema":1}`), []byte(`null`), make([]byte, alpha.MaxManifestBytes+1)} {
		_, libraryErr := alpha.VerifyTrustTransition(tc, sig, pub, alpha.VerifyOptions{Now: now})
		_, cliErr := verifyManifest(tc, sig, pub, alpha.VerifyOptions{Now: now})
		if (libraryErr != nil) != (cliErr != nil) || libraryErr == nil {
			t.Fatal("CLI/library acceptance drift")
		}
	}
}
func TestReadBoundAndCreateOnce(t *testing.T) {
	d := t.TempDir()
	if err := os.WriteFile(filepath.Join(d, "large.json"), make([]byte, alpha.MaxManifestBytes+1), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readManifest(filepath.Join(d, "large.json")); err == nil {
		t.Fatal("oversize manifest read")
	}
	if err := writePair(d, []byte("manifest"), []byte("signature")); err != nil {
		t.Fatal(err)
	}
	if err := writePair(d, []byte("replacement"), []byte("replacement")); err == nil {
		t.Fatal("overwrote pair")
	}
}
