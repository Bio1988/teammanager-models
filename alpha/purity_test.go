package alpha

import (
	"go/parser"
	"go/token"
	"path/filepath"
	"testing"
)

func TestPurePackageHasNoRuntimeBoundaryImports(t *testing.T) {
	forbidden := map[string]bool{"os": true, "os/exec": true, "net": true, "net/http": true, "path/filepath": true}
	files, err := filepath.Glob("*.go")
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range files {
		if filepath.Base(name) == "purity_test.go" {
			continue
		}
		f, err := parser.ParseFile(token.NewFileSet(), name, nil, parser.ImportsOnly)
		if err != nil {
			t.Fatal(err)
		}
		for _, imp := range f.Imports {
			if forbidden[imp.Path.Value[1:len(imp.Path.Value)-1]] {
				t.Fatalf("pure package imports %s in %s", imp.Path.Value, name)
			}
		}
	}
}
