package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
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
	unknownBeforeDuplicate := []byte(strings.Replace(string(b), `{"schema":1`, `{"unknown":true,"schema":1`, 1))
	unknownBeforeDuplicate = append(unknownBeforeDuplicate[:len(unknownBeforeDuplicate)-1], []byte(`,"schema":1}`)...)
	typeBeforeUnknown := []byte(strings.Replace(string(b), `"schema":1`, `"schema":{"x":1}`, 1))
	typeBeforeUnknown = append(typeBeforeUnknown[:len(typeBeforeUnknown)-1], []byte(`,"unknown":true}`)...)
	nestedTypeBeforeUnknown := []byte(strings.Replace(string(b), `"status":"active"`, `"status":{"x":1}`, 1))
	nestedTypeBeforeUnknown = append(nestedTypeBeforeUnknown[:len(nestedTypeBeforeUnknown)-1], []byte(`,"unknown":true}`)...)
	unknownBeforeNestedDuplicate := []byte(strings.Replace(string(b), `{"schema":1`, `{"unknown":true,"schema":1`, 1))
	unknownBeforeNestedDuplicate = []byte(strings.Replace(string(unknownBeforeNestedDuplicate), `"status":"active"`, `"status":"active","status":"active"`, 1))
	for _, tc := range []struct {
		name     string
		manifest []byte
		want     string
	}{
		{"unknown", unknown, `json: unknown field "unknown"`},
		{"unknown before duplicate", unknownBeforeDuplicate, `duplicate JSON key "schema"`},
		{"unknown before nested duplicate", unknownBeforeNestedDuplicate, `duplicate JSON key "status"`},
		{"type before unknown", typeBeforeUnknown, "manifest.schema"},
		{"nested type before unknown", nestedTypeBeforeUnknown, "keyRotation.key_rotation.status"},
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

func candidateRelease(product, repo, filename string, contents []byte) alpha.Release {
	r := testRelease(product, repo, filename)
	r.Size = int64(len(contents))
	sum := sha256.Sum256(contents)
	r.SHA256 = hex.EncodeToString(sum[:])
	return r
}

type failingCandidateFile struct {
	file      *os.File
	stream    []byte
	offset    int
	readErr   error
	statErrAt int
	closeErr  error
	stats     int
}

func (f *failingCandidateFile) Read(p []byte) (int, error) {
	if f.readErr != nil {
		return 0, f.readErr
	}
	if f.stream != nil {
		if f.offset >= len(f.stream) {
			return 0, io.EOF
		}
		n := copy(p, f.stream[f.offset:])
		f.offset += n
		return n, nil
	}
	return f.file.Read(p)
}
func (f *failingCandidateFile) Stat() (os.FileInfo, error) {
	f.stats++
	if f.stats == f.statErrAt {
		return nil, errors.New("injected stat")
	}
	return f.file.Stat()
}
func (f *failingCandidateFile) Close() error {
	err := f.file.Close()
	if f.closeErr != nil {
		return f.closeErr
	}
	return err
}
func TestVerifyCandidateReachableHandleErrors(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path := filepath.Join(d, r.Filename)
	for _, tc := range []struct {
		name, want string
		readErr    error
		statErrAt  int
		closeErr   error
	}{{"read", "cannot be read", errors.New("read"), 0, nil}, {"pre stat", "cannot be stated", nil, 1, nil}, {"post stat", "cannot be re-stated", nil, 2, nil}, {"close", "cannot be closed", nil, 0, errors.New("close")}} {
		t.Run(tc.name, func(t *testing.T) {
			if err := os.WriteFile(path, contents, 0600); err != nil {
				t.Fatal(err)
			}
			ops := candidateOps{lstat: os.Lstat, sameFile: os.SameFile, open: func(name string) (candidateFile, error) {
				f, err := os.Open(name)
				if err != nil {
					return nil, err
				}
				return &failingCandidateFile{file: f, readErr: tc.readErr, statErrAt: tc.statErrAt, closeErr: tc.closeErr}, nil
			}}
			err := verifyCandidateWithOps(path, r, ops)
			if err == nil || !contains(err.Error(), tc.want) {
				t.Fatalf("wanted %q, got %v", tc.want, err)
			}
		})
	}
}
func TestVerifyCandidateObservedStreamGates(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path := filepath.Join(d, r.Filename)
	for _, tc := range []struct {
		name, want string
		stream     []byte
	}{{name: "truncated", stream: contents[:len(contents)-1], want: "truncated"}, {name: "appended", stream: append(append([]byte{}, contents...), 'x'), want: "grew"}, {name: "same-size tamper", stream: append([]byte("x"), contents[1:]...), want: "SHA-256"}} {
		t.Run(tc.name, func(t *testing.T) {
			if err := os.WriteFile(path, contents, 0600); err != nil {
				t.Fatal(err)
			}
			ops := candidateOps{lstat: os.Lstat, sameFile: os.SameFile, open: func(name string) (candidateFile, error) {
				f, err := os.Open(name)
				if err != nil {
					return nil, err
				}
				return &failingCandidateFile{file: f, stream: tc.stream}, nil
			}}
			err := verifyCandidateWithOps(path, r, ops)
			if err == nil || !contains(err.Error(), tc.want) {
				t.Fatalf("wanted %q, got %v", tc.want, err)
			}
		})
	}
}
func TestVerifyCandidateRejectsUnsafeOrMismatchedFiles(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path := filepath.Join(d, r.Filename)
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}
	if err := verifyCandidate(path, r); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(path); err != nil {
		t.Fatalf("verified handle was not closed: %v", err)
	}
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}
	tampered := append([]byte{}, contents...)
	tampered[0] ^= 1
	if err := os.WriteFile(path, tampered, 0600); err != nil {
		t.Fatal(err)
	}
	if err := verifyCandidate(path, r); err == nil {
		t.Fatal("accepted tampered candidate")
	}
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}
	if err := verifyCandidate(filepath.Join(d, "wrong.exe"), r); err == nil {
		t.Fatal("accepted wrong basename")
	}
	if err := verifyCandidate(filepath.Join(d, "missing-parent", r.Filename), r); err == nil {
		t.Fatal("accepted missing candidate")
	}
	dirCandidate := filepath.Join(d, "dir", r.Filename)
	if err := os.MkdirAll(dirCandidate, 0700); err != nil {
		t.Fatal(err)
	}
	if err := verifyCandidate(dirCandidate, r); err == nil {
		t.Fatal("accepted directory")
	}
	r.Size++
	if err := verifyCandidate(path, r); err == nil {
		t.Fatal("accepted wrong size")
	}
	r.Size--
	r.SHA256 = strings.Repeat("0", 64)
	if err := verifyCandidate(path, r); err == nil {
		t.Fatal("accepted wrong hash")
	}
	link := filepath.Join(d, "RaceSetup-link.exe")
	if err := os.Symlink(path, link); err != nil {
		if runtime.GOOS != "windows" {
			t.Fatalf("cannot create mandatory symlink: %v", err)
		}
		t.Logf("Windows symlink check skipped: %v", err)
	} else if err := verifyCandidate(link, candidateRelease("race_engineer", "race-engineer-go", "RaceSetup-link.exe", contents)); err == nil {
		t.Fatal("accepted symlink")
	}
	r.Size = 1 << 62
	if err := verifyCandidate(path, r); err == nil {
		t.Fatal("accepted huge signed size")
	}
}
func TestVerifyCandidateRejectsFinalPathSwap(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path, replacement := filepath.Join(d, r.Filename), filepath.Join(d, "replacement.exe")
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(replacement, contents, 0600); err != nil {
		t.Fatal(err)
	}
	calls := 0
	err := verifyCandidateWithOps(path, r, candidateOps{lstat: func(name string) (os.FileInfo, error) {
		calls++
		if calls == 2 {
			if err := os.Remove(path); err != nil {
				return nil, err
			}
			if err := os.Rename(replacement, path); err != nil {
				return nil, err
			}
		}
		return os.Lstat(name)
	}, open: func(name string) (candidateFile, error) { return os.Open(name) }, sameFile: os.SameFile})
	if err == nil || !contains(err.Error(), "path changed") {
		t.Fatalf("accepted final path swap: %v", err)
	}
}
func TestVerifyCandidateCommandTrustsBeforeCandidateReads(t *testing.T) {
	d := t.TempDir()
	now := time.Now().UTC()
	raceBytes, relayBytes := []byte("race"), []byte("relay")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", raceBytes)
	l := candidateRelease("relay", "teammanager-relay", "RelaySetup.exe", relayBytes)
	m := alpha.Manifest{Schema: 1, Channel: "alpha", KeyID: "alpha-1", KeyRotation: alpha.KeyRotation{Status: "active", NotBefore: now.Add(-time.Hour).Format(time.RFC3339), NotAfter: now.Add(time.Hour).Format(time.RFC3339)}, GeneratedAt: now.Add(-time.Minute).Format(time.RFC3339), ExpiresAt: now.Add(time.Hour).Format(time.RFC3339), ReleaseSequence: 7, AuthenticodePolicy: "not-required", RaceEngineer: r, Relay: l}
	manifest, _ := json.Marshal(m)
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	manifestPath, sigPath, keyPath := filepath.Join(d, "alpha.json"), filepath.Join(d, "alpha.json.sig"), filepath.Join(d, "alpha.pub")
	if err := os.WriteFile(manifestPath, manifest, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv, alpha.SignedPayload(manifest)))), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(keyPath, []byte(base64.StdEncoding.EncodeToString(pub)), 0600); err != nil {
		t.Fatal(err)
	}
	racePath, relayPath := filepath.Join(d, r.Filename), filepath.Join(d, l.Filename)
	if err := os.WriteFile(racePath, raceBytes, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(relayPath, relayBytes, 0600); err != nil {
		t.Fatal(err)
	}
	args := []string{"run", ".", "verify-candidate", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath, "--race-installer", racePath, "--relay-installer", relayPath, "--min-sequence", "6"}
	out, err := exec.Command("go", args...).CombinedOutput()
	if err != nil || !contains(string(out), "verified candidate race_engineer") {
		t.Fatalf("candidate command failed: %v %s", err, out)
	}
	args = append(args, "--min-sequence", "7")
	out, err = exec.Command("go", args...).CombinedOutput()
	if err == nil || !contains(string(out), "release_sequence is not newer") {
		t.Fatalf("candidate replay check failed: %v %s", err, out)
	}
	args = args[:len(args)-2]
	badSig := ed25519.Sign(priv, alpha.SignedPayload(manifest))
	badSig[0] ^= 1
	if err := os.Remove(racePath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(relayPath); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(badSig)), 0600); err != nil {
		t.Fatal(err)
	}
	out, err = exec.Command("go", args...).CombinedOutput()
	if err == nil || !contains(string(out), "invalid detached signature") || contains(string(out), "cannot be inspected") {
		t.Fatalf("trust failure read candidate: %v %s", err, out)
	}
}

func TestVerifyCandidateCommandOptionParityOrderingAndPrivateOutput(t *testing.T) {
	d := t.TempDir()
	now := time.Now().UTC()
	raceBytes, relayBytes := []byte("race candidate"), []byte("relay candidate")
	race := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", raceBytes)
	relay := candidateRelease("relay", "teammanager-relay", "RelaySetup.exe", relayBytes)
	m := alpha.Manifest{Schema: 1, Channel: "alpha", KeyID: "alpha-1", KeyRotation: alpha.KeyRotation{Status: "active", NotBefore: now.Add(-time.Hour).Format(time.RFC3339), NotAfter: now.Add(time.Hour).Format(time.RFC3339)}, GeneratedAt: now.Add(-time.Minute).Format(time.RFC3339), ExpiresAt: now.Add(time.Hour).Format(time.RFC3339), ReleaseSequence: 7, AuthenticodePolicy: "not-required", RaceEngineer: race, Relay: relay}
	manifest, err := json.Marshal(m)
	if err != nil {
		t.Fatal(err)
	}
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	manifestPath, sigPath, keyPath := filepath.Join(d, "alpha.json"), filepath.Join(d, "alpha.json.sig"), filepath.Join(d, "alpha.pub")
	if err := os.WriteFile(manifestPath, manifest, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(ed25519.Sign(priv, alpha.SignedPayload(manifest)))), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(keyPath, []byte(base64.StdEncoding.EncodeToString(pub)), 0600); err != nil {
		t.Fatal(err)
	}
	racePath, relayPath := filepath.Join(d, race.Filename), filepath.Join(d, relay.Filename)
	if err := os.WriteFile(racePath, raceBytes, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(relayPath, relayBytes, 0600); err != nil {
		t.Fatal(err)
	}
	base := []string{"run", ".", "verify-candidate", "--manifest", manifestPath, "--signature", sigPath, "--public-key", keyPath, "--race-installer", racePath, "--relay-installer", relayPath}
	run := func(extra ...string) (string, error) { return runAlphaChannel(base, extra...) }
	if out, err := run("--min-sequence", "6", "--race-version", "0.1.0-alpha.6", "--relay-version", "0.1.0-alpha.6"); err != nil || !contains(out, "verified candidate") {
		t.Fatalf("all shared trust flags must succeed: %v %s", err, out)
	}
	if err := os.Remove(racePath); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(relayPath); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name, want string
		extra      []string
	}{
		{"replay before race", "release_sequence is not newer", []string{"--min-sequence", "7"}},
		{"race downgrade before race", "race_engineer version is not newer", []string{"--race-version", "0.1.0-alpha.7"}},
		{"relay downgrade before race", "relay version is not newer", []string{"--race-version", "0.1.0-alpha.6", "--relay-version", "0.1.0-alpha.7"}},
		{"race before relay", "race_engineer candidate cannot be inspected", nil},
	} {
		t.Run(tc.name, func(t *testing.T) {
			out, err := run(tc.extra...)
			if err == nil || !contains(out, tc.want) || contains(out, relay.Filename) {
				t.Fatalf("want %q before candidate IO, err=%v output=%s", tc.want, err, out)
			}
		})
	}
	if err := os.WriteFile(racePath, raceBytes, 0600); err != nil {
		t.Fatal(err)
	}
	out, err := run()
	if err == nil || !contains(out, "relay candidate cannot be inspected") {
		t.Fatalf("relay was not checked after successful race: %v %s", err, out)
	}
	bad := ed25519.Sign(priv, alpha.SignedPayload(manifest))
	bad[0] ^= 1 // stays exactly ed25519.SignatureSize; this is a crypto failure, not a parse failure.
	if err := os.WriteFile(sigPath, []byte(base64.StdEncoding.EncodeToString(bad)), 0600); err != nil {
		t.Fatal(err)
	}
	out, err = run()
	if err == nil || !contains(out, "invalid detached signature") || contains(out, racePath) || contains(out, keyPath) || contains(out, sigPath) || contains(out, string(manifest)) || contains(out, base64.StdEncoding.EncodeToString(bad)) {
		t.Fatalf("trust error disclosed input or reached candidates: %v %s", err, out)
	}
}

func runAlphaChannel(base []string, extra ...string) (string, error) {
	args := append(append([]string{}, base...), extra...)
	out, err := exec.Command("go", args...).CombinedOutput()
	return string(out), err
}

func TestVerifyCandidateFinalIdentityAndNoWriteSnapshot(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path := filepath.Join(d, r.Filename)
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(d, "nested"), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(d, "nested", "sentinel"), []byte("untouched"), 0600); err != nil {
		t.Fatal(err)
	}
	before := treeSnapshot(t, d)
	calls := 0
	err := verifyCandidateWithOps(path, r, candidateOps{
		lstat:    os.Lstat,
		open:     func(name string) (candidateFile, error) { return os.Open(name) },
		sameFile: func(a, b os.FileInfo) bool { calls++; return calls != 3 && os.SameFile(a, b) },
	})
	if err == nil || !contains(err.Error(), "path changed during verification") || calls != 3 {
		t.Fatalf("final identity gate/counter mismatch: err=%v calls=%d", err, calls)
	}
	after := treeSnapshot(t, d)
	if len(before) != len(after) {
		t.Fatalf("verifier wrote tree: before=%v after=%v", before, after)
	}
	for name, sum := range before {
		if after[name] != sum {
			t.Fatalf("verifier wrote %s", name)
		}
	}
}

func treeSnapshot(t *testing.T, root string) map[string]string {
	t.Helper()
	out := map[string]string{}
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, path)
		if err != nil {
			return err
		}
		if info.IsDir() {
			out[rel] = "dir"
			return nil
		}
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		s := sha256.Sum256(b)
		out[rel] = info.Mode().String() + ":" + hex.EncodeToString(s[:])
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	return out
}

func TestVerifyCandidateRejectsInvalidSignedSizeBeforeArtifactIO(t *testing.T) {
	contents := []byte("candidate installer")
	base := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	for _, tc := range []struct {
		name string
		size int64
	}{
		{"zero", 0},
		{"over eight GiB", (8 << 30) + 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := base
			r.Size = tc.size
			lstats, opens := 0, 0
			err := verifyCandidateWithOps("RaceSetup.exe", r, candidateOps{
				lstat:    func(string) (os.FileInfo, error) { lstats++; return nil, errors.New("must not inspect") },
				open:     func(string) (candidateFile, error) { opens++; return nil, errors.New("must not open") },
				sameFile: os.SameFile,
			})
			if err == nil || !contains(err.Error(), "signed size is outside") || lstats != 0 || opens != 0 {
				t.Fatalf("err=%v, lstats=%d, opens=%d", err, lstats, opens)
			}
		})
	}

	// The upper bound itself is allowed to reach the artifact gate without an
	// allocation proportional to signed size.  The fake file stops at Stat.
	r := base
	r.Size = 8 << 30
	info, err := os.Stat(os.Args[0])
	if err != nil {
		t.Fatal(err)
	}
	opens := 0
	err = verifyCandidateWithOps("RaceSetup.exe", r, candidateOps{
		lstat: func(string) (os.FileInfo, error) { return info, nil },
		open: func(string) (candidateFile, error) {
			opens++
			f, err := os.Open(os.Args[0])
			if err != nil {
				return nil, err
			}
			return f, nil
		},
		sameFile: func(_, _ os.FileInfo) bool { return true },
	})
	if err == nil || !contains(err.Error(), "size does not match") || opens != 1 {
		t.Fatalf("max size did not reach artifact gate: err=%v opens=%d", err, opens)
	}
}

func TestVerifyCandidatePrivateOpsErrorsCloseHandles(t *testing.T) {
	d := t.TempDir()
	contents := []byte("candidate installer")
	r := candidateRelease("race_engineer", "race-engineer-go", "RaceSetup.exe", contents)
	path := filepath.Join(d, r.Filename)
	if err := os.WriteFile(path, contents, 0600); err != nil {
		t.Fatal(err)
	}

	for _, tc := range []struct {
		name, want          string
		configure           func(*candidateOps, *int)
		wantOpen, wantClose int
	}{
		{"initial lstat", "cannot be inspected", func(o *candidateOps, _ *int) {
			o.lstat = func(string) (os.FileInfo, error) { return nil, errors.New("lstat") }
		}, 0, 0},
		{"open", "cannot be opened", func(o *candidateOps, _ *int) {
			o.open = func(string) (candidateFile, error) { return nil, errors.New("open") }
		}, 1, 0},
		{"initial handle stat", "cannot be stated", func(o *candidateOps, _ *int) { o.open = trackedOpen(path, 1, nil) }, 1, 0},
		{"initial identity", "changed before", func(o *candidateOps, _ *int) { o.sameFile = func(_, _ os.FileInfo) bool { return false } }, 1, 1},
		{"read", "cannot be read", func(o *candidateOps, _ *int) { o.open = trackedOpen(path, 0, errors.New("read")) }, 1, 0},
		{"final handle stat", "cannot be re-stated", func(o *candidateOps, _ *int) { o.open = trackedOpen(path, 2, nil) }, 1, 0},
		{"close", "cannot be closed", func(o *candidateOps, _ *int) {
			o.open = func(string) (candidateFile, error) {
				f, e := os.Open(path)
				if e != nil {
					return nil, e
				}
				return &failingCandidateFile{file: f, closeErr: errors.New("close")}, nil
			}
		}, 1, 0},
		{"final lstat", "cannot be finally inspected", func(o *candidateOps, _ *int) {
			calls := 0
			o.lstat = func(name string) (os.FileInfo, error) {
				calls++
				if calls == 2 {
					return nil, errors.New("final")
				}
				return os.Lstat(name)
			}
		}, 1, 1},
	} {
		t.Run(tc.name, func(t *testing.T) {
			opens, closes := 0, 0
			op := candidateOps{lstat: os.Lstat, open: func(name string) (candidateFile, error) {
				f, e := os.Open(name)
				if e != nil {
					return nil, e
				}
				return &closeCountingFile{File: f, closes: &closes}, nil
			}, sameFile: os.SameFile}
			tc.configure(&op, &closes)
			// Configured open functions are still counted at the seam boundary.
			originalOpen := op.open
			op.open = func(name string) (candidateFile, error) { opens++; return originalOpen(name) }
			err := verifyCandidateWithOps(path, r, op)
			if err == nil || !contains(err.Error(), tc.want) || opens != tc.wantOpen {
				t.Fatalf("err=%v opens=%d", err, opens)
			}
			if tc.wantClose != 0 && tc.name != "close" && closes != tc.wantClose {
				t.Fatalf("handle leaked after %s: closes=%d", tc.name, closes)
			}
			released := path + ".released"
			if renameErr := os.Rename(path, released); renameErr != nil {
				t.Fatalf("handle was not releasable: %v", renameErr)
			}
			if renameErr := os.Rename(released, path); renameErr != nil {
				t.Fatal(renameErr)
			}
		})
	}
}

type closeCountingFile struct {
	*os.File
	closes *int
}

func (f *closeCountingFile) Close() error { *f.closes++; return f.File.Close() }

func trackedOpen(path string, statErrAt int, readErr error) func(string) (candidateFile, error) {
	return func(string) (candidateFile, error) {
		f, err := os.Open(path)
		if err != nil {
			return nil, err
		}
		return &failingCandidateFile{file: f, statErrAt: statErrAt, readErr: readErr}, nil
	}
}
