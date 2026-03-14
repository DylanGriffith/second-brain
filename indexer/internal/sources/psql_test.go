package sources_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/sources"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

func TestPsqlCollectNew_Basic(t *testing.T) {
	src := sources.NewPsqlSourceWithPath("testdata/psql_history")
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) == 0 {
		t.Fatal("expected docs, got none")
	}
	for _, d := range docs {
		if d.GlobalID[:13] != "psql_history:" {
			t.Errorf("wrong prefix: %s", d.GlobalID)
		}
		if d.Domain != "psql" {
			t.Errorf("expected domain 'psql', got '%s'", d.Domain)
		}
	}
}

func TestPsqlCollectNew_Resume(t *testing.T) {
	src := sources.NewPsqlSourceWithPath("testdata/psql_history")
	st := &state.SourceState{}
	docs1, _ := src.CollectNew(st)
	docs2, _ := src.CollectNew(st)
	if len(docs2) != 0 {
		t.Errorf("expected 0 new docs on second sync, got %d (from %d total)", len(docs2), len(docs1))
	}
}

func TestPsqlCollectNew_MultilineSQL(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "psql_history")
	// psql stores multi-line as literal \n
	os.WriteFile(path, []byte("SELECT *\nFROM users\nWHERE id = 1;\n"), 0644)

	src := sources.NewPsqlSourceWithPath(path)
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	// Should have 3 lines (each line is a separate entry in raw psql_history)
	if len(docs) == 0 {
		t.Fatal("expected docs")
	}
}
