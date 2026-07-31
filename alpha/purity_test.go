package alpha

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

var allowedImports = map[string]bool{"bytes": true, "crypto/ed25519": true, "encoding/json": true, "errors": true, "fmt": true, "io": true, "regexp": true, "strconv": true, "strings": true, "time": true, "unicode/utf8": true}
var allowedSelectors = map[string]map[string]bool{"fmt": {"Errorf": true}, "time": {"Minute": true, "Parse": true, "RFC3339": true, "Time": true, "UTC": true}}

func TestPurePackageImportsOnlyApprovedStdlib(t *testing.T) {
	for _, name := range productionGoFiles(t) {
		b, err := os.ReadFile(name)
		if err != nil {
			t.Fatal(err)
		}
		if err := checkPureSource(name, b); err != nil {
			t.Fatal(err)
		}
	}
}
func TestPuritySentinelRejectsBoundaryMutations(t *testing.T) {
	for name, source := range map[string]string{
		"alias now":      `package alpha; import t "time"; func f() { _ = t.Now() }`,
		"implicit clock": `package alpha; import "time"; func f() { _ = time.After(time.Second); _ = time.Since(time.Time{}); time.Sleep(time.Second) }`,
		"dot time":       `package alpha; import . "time"; func f() { _ = Now() }`,
		"blank import":   `package alpha; import _ "net/http"`,
		"load location":  `package alpha; import "time"; func f() { _, _ = time.LoadLocation("Local") }`,
		"print":          `package alpha; import p "fmt"; func f() { p.Println("side effect") }`,
		"scan":           `package alpha; import "fmt"; func f() { var s string; _, _ = fmt.Scan(&s) }`,
	} {
		if err := checkPureSource(name, []byte(source)); err == nil {
			t.Fatalf("accepted %s", name)
		}
	}
}
func checkPureSource(name string, source []byte) error {
	f, err := parser.ParseFile(token.NewFileSet(), name, source, 0)
	if err != nil {
		return err
	}
	aliases := map[string]string{}
	for _, imp := range f.Imports {
		path := strings.Trim(imp.Path.Value, `"`)
		if !allowedImports[path] {
			return fmt.Errorf("pure package imports non-approved dependency %q", path)
		}
		if imp.Name != nil && (imp.Name.Name == "." || imp.Name.Name == "_") {
			return fmt.Errorf("pure package uses forbidden import form %q", imp.Name.Name)
		}
		alias := path[strings.LastIndex(path, "/")+1:]
		if imp.Name != nil {
			alias = imp.Name.Name
		}
		aliases[alias] = path
	}
	var violation error
	ast.Inspect(f, func(n ast.Node) bool {
		selector, ok := n.(*ast.SelectorExpr)
		if !ok || violation != nil {
			return violation == nil
		}
		ident, ok := selector.X.(*ast.Ident)
		if !ok {
			return true
		}
		path := aliases[ident.Name]
		if allowed, constrained := allowedSelectors[path]; constrained && !allowed[selector.Sel.Name] {
			violation = fmt.Errorf("pure package uses non-approved %s.%s", path, selector.Sel.Name)
		}
		return violation == nil
	})
	return violation
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
