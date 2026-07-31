package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
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
	if err := os.WriteFile(filepath.Join(d, "large.sig"), make([]byte, alpha.MaxSignatureBytes+1), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := readSignature(filepath.Join(d, "large.sig")); err == nil {
		t.Fatal("oversized signature accepted")
	}
}
func TestPairFailureCleansItsManifest(t *testing.T) {
	d := t.TempDir()
	if err := os.WriteFile(filepath.Join(d, "alpha.json.sig"), []byte("existing"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := writePair(d, []byte("manifest"), []byte("signature")); err == nil {
		t.Fatal("accepted existing signature")
	}
	if _, err := os.Stat(filepath.Join(d, "alpha.json")); !os.IsNotExist(err) {
		t.Fatalf("partial manifest remains: %v", err)
	}
	got, err := os.ReadFile(filepath.Join(d, "alpha.json.sig"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "existing" {
		t.Fatal("existing signature changed")
	}
}
func TestVerifyCommandReadsFilesAndPreservesLibraryResult(t *testing.T) {
	d := t.TempDir()
	now := time.Now().UTC()
	b := manifestBytes(now)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	sig := ed25519.Sign(priv, alpha.SignedPayload(b))
	manifestPath := filepath.Join(d, "alpha.json")
	sigPath := filepath.Join(d, "alpha.json.sig")
	keyPath := filepath.Join(d, "alpha.pub")
	if err := os.WriteFile(manifestPath, b, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(sig)), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(keyPath, []byte(base64.StdEncoding.EncodeToString(pub)), 0600); err != nil {
		t.Fatal(err)
	}
	args := []string{"run", ".", "verify", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath, "--min-sequence", "6", "--race-version", "0.1.0-alpha.6", "--relay-version", "0.1.0-alpha.6"}
	cmd := exec.Command("go", args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("verify command failed: %v\n%s", err, out)
	}
	if string(out) == "" || !contains(string(out), "verified alpha channel sequence 7") {
		t.Fatalf("unexpected output: %s", out)
	}
	args = append(args, "--min-sequence", "7")
	cmd = exec.Command("go", args...)
	out, err = cmd.CombinedOutput()
	if err == nil || !contains(string(out), "release_sequence is not newer") {
		t.Fatalf("expected CLI trust rejection, err=%v output=%s", err, out)
	}
	if err := os.WriteFile(manifestPath, make([]byte, alpha.MaxManifestBytes+1), 0600); err != nil {
		t.Fatal(err)
	}
	cmd = exec.Command("go", "run", ".", "verify", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath)
	out, err = cmd.CombinedOutput()
	if err == nil || !contains(string(out), "manifest exceeds 64 KiB") {
		t.Fatalf("expected manifest boundary error, err=%v output=%s", err, out)
	}
	typeError := []byte(strings.Replace(string(b), `"schema":1`, `"schema":"1"`, 1))
	if err := os.WriteFile(manifestPath, typeError, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv, alpha.SignedPayload(typeError)))), 0600); err != nil {
		t.Fatal(err)
	}
	cmd = exec.Command("go", "run", ".", "verify", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath)
	out, err = cmd.CombinedOutput()
	if err == nil || !contains(string(out), "struct field manifest.schema") {
		t.Fatalf("expected legacy JSON type error, err=%v output=%s", err, out)
	}
	var object map[string]any
	if err := json.Unmarshal(b, &object); err != nil {
		t.Fatal(err)
	}
	keyRotationType := cloneObject(t, object)
	keyRotationType["key_rotation"] = "wrong"
	releaseType := cloneObject(t, object)
	releaseType["race_engineer"] = "wrong"
	keyRotationScalar := cloneObject(t, object)
	keyRotationScalar["key_rotation"].(map[string]any)["status"] = 1
	raceReleaseScalar := cloneObject(t, object)
	raceReleaseScalar["race_engineer"].(map[string]any)["product"] = 1
	relayReleaseScalar := cloneObject(t, object)
	relayReleaseScalar["relay"].(map[string]any)["filename"] = 1
	schemaObject := cloneObject(t, object)
	schemaObject["schema"] = map[string]any{"x": 1}
	schemaArray := cloneObject(t, object)
	schemaArray["schema"] = []any{1}
	keyRotationObject := cloneObject(t, object)
	keyRotationObject["key_rotation"].(map[string]any)["status"] = map[string]any{"x": 1}
	raceReleaseArray := cloneObject(t, object)
	raceReleaseArray["race_engineer"].(map[string]any)["product"] = []any{"race_engineer"}
	unknown := append(append([]byte{}, b[:len(b)-1]...), []byte(`,"unknown":true}`)...)
	for _, tc := range []struct {
		name     string
		manifest []byte
		want     string
	}{
		{"unknown", unknown, `json: unknown field "unknown"`},
		{"root", []byte(`[]`), "Go value of type main.manifest"},
		{"key rotation type", marshalObject(t, keyRotationType), "type main.keyRotation"},
		{"release type", marshalObject(t, releaseType), "type main.release"},
		{"key rotation scalar", marshalObject(t, keyRotationScalar), "keyRotation.key_rotation.status"},
		{"race release scalar", marshalObject(t, raceReleaseScalar), "release.race_engineer.product"},
		{"relay release scalar", marshalObject(t, relayReleaseScalar), "release.relay.filename"},
		{"schema object", marshalObject(t, schemaObject), "manifest.schema"},
		{"schema array", marshalObject(t, schemaArray), "manifest.schema"},
		{"key rotation object", marshalObject(t, keyRotationObject), "keyRotation.key_rotation.status"},
		{"release array", marshalObject(t, raceReleaseArray), "release.race_engineer.product"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			if err := os.WriteFile(manifestPath, tc.manifest, 0600); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv, alpha.SignedPayload(tc.manifest)))), 0600); err != nil {
				t.Fatal(err)
			}
			cmd := exec.Command("go", "run", ".", "verify", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath)
			out, err := cmd.CombinedOutput()
			if err == nil || !contains(string(out), tc.want) {
				t.Fatalf("expected %q, err=%v output=%s", tc.want, err, out)
			}
		})
	}
}
func contains(s, want string) bool {
	return len(s) >= len(want) && (s == want || strings.Contains(s, want))
}
func cloneObject(t *testing.T, value map[string]any) map[string]any {
	t.Helper()
	b := marshalObject(t, value)
	var copy map[string]any
	if err := json.Unmarshal(b, &copy); err != nil {
		t.Fatal(err)
	}
	return copy
}
func marshalObject(t *testing.T, value map[string]any) []byte {
	t.Helper()
	b, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	return b
}
