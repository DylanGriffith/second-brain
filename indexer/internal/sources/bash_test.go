package sources_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/sources"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

func TestBashCollectNew_Basic(t *testing.T) {
	src := sources.NewBashSourceWithPath("testdata/bash_history")
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) == 0 {
		t.Fatal("expected docs, got none")
	}
	// Verify global_id format
	for _, d := range docs {
		if len(d.GlobalID) < len("bash_history:") {
			t.Errorf("bad global_id: %s", d.GlobalID)
		}
		if d.GlobalID[:13] != "bash_history:" {
			t.Errorf("wrong prefix in global_id: %s", d.GlobalID)
		}
	}
}

func TestBashCollectNew_Resume(t *testing.T) {
	src := sources.NewBashSourceWithPath("testdata/bash_history")

	// First sync - get all
	st := &state.SourceState{}
	docs1, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("first sync failed: %v", err)
	}
	firstCount := len(docs1)

	// Second sync - should get nothing new (same file)
	docs2, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("second sync failed: %v", err)
	}
	if len(docs2) != 0 {
		t.Errorf("expected 0 new docs on second sync, got %d (from %d total)", len(docs2), firstCount)
	}
}

func TestBashCollectNew_TitleTruncation(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "bash_history")
	longCmd := "echo " + string(make([]byte, 100))
	os.WriteFile(path, []byte(longCmd+"\n"), 0644)

	src := sources.NewBashSourceWithPath(path)
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) != 1 {
		t.Fatalf("expected 1 doc, got %d", len(docs))
	}
	if len(docs[0].Title) > 50 {
		t.Errorf("title not truncated: len=%d", len(docs[0].Title))
	}
	if docs[0].Snippet != longCmd {
		t.Errorf("snippet should be full command")
	}
}

func TestBashCollectNew_EmptyFile(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "bash_history_empty")
	os.WriteFile(path, []byte(""), 0644)

	src := sources.NewBashSourceWithPath(path)
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) != 0 {
		t.Errorf("expected 0 docs for empty file, got %d", len(docs))
	}
}
