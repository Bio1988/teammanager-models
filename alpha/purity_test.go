package alpha

import (
	"go/ast"
	"go/parser"
	"go/token"
	"path/filepath"
	"strings"
	"testing"
)

func TestPurePackageImportsOnlyApprovedStdlib(t *testing.T) {
	allowed := map[string]bool{
		"bytes": true, "crypto/ed25519": true, "encoding/json": true,
		"errors": true, "fmt": true, "io": true, "regexp": true,
		"strconv": true, "strings": true, "time": true, "unicode/utf8": true,
	}
	for _, name := range productionGoFiles(t) {
		f, err := parser.ParseFile(token.NewFileSet(), name, nil, 0)
		if err != nil {
			t.Fatal(err)
		}
		for _, imp := range f.Imports {
			path := strings.Trim(imp.Path.Value, `"`)
			if !allowed[path] {
				t.Fatalf("pure package imports non-approved dependency %q in %s", path, name)
			}
		}
	}
}

func TestPurePackageUsesOnlyInjectedTime(t *testing.T) {
	for _, name := range productionGoFiles(t) {
		f, err := parser.ParseFile(token.NewFileSet(), name, nil, 0)
		if err != nil {
			t.Fatal(err)
		}
		ast.Inspect(f, func(n ast.Node) bool {
			selector, ok := n.(*ast.SelectorExpr)
			if !ok || selector.Sel.Name != "Now" {
				return true
			}
			if ident, ok := selector.X.(*ast.Ident); ok && ident.Name == "time" {
				t.Fatalf("non-injected time.Now in %s", name)
			}
			return true
		})
	}
}

func productionGoFiles(t *testing.T) []string {
	t.Helper()
	files, err := filepath.Glob("*.go")
	if err != nil {
		t.Fatal(err)
	}
	var production []string
	for _, name := range files {
		if !strings.HasSuffix(name, "_test.go") {
			production = append(production, name)
		}
	}
	return production
}
