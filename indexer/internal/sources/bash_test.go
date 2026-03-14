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
	for _, d := range docs {
		if d.GlobalID[:13] != "bash_history:" {
			t.Errorf("wrong prefix in global_id: %s", d.GlobalID)
		}
	}
}

// TestBashCollectNew_ResumeWithTrailingSpacesAndEmptyLines is the core regression
// test for the resume bug. The raw history file has:
//   - trailing spaces on some lines (e.g. "nvim file.go ")
//   - blank lines between commands
//
// Previously, allLines was built from the raw split (including empty strings and
// untrimmed lines) while LastLines stored trimmed non-empty lines, so matchesAt
// comparisons always failed and every sync restarted from line 0.
func TestBashCollectNew_ResumeWithTrailingSpacesAndEmptyLines(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "bash_history")

	// Write history with trailing spaces and a blank line — mirroring real bash history.
	initial := "git status\nnvim README.md \ngo build ./...  \n\ngo test ./...\n"
	os.WriteFile(path, []byte(initial), 0644)

	src := sources.NewBashSourceWithPath(path)
	st := &state.SourceState{}

	docs1, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("first sync failed: %v", err)
	}
	if len(docs1) != 4 {
		t.Fatalf("expected 4 docs on first sync, got %d", len(docs1))
	}

	// Second sync: same file, no new lines — must return 0.
	docs2, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("second sync failed: %v", err)
	}
	if len(docs2) != 0 {
		t.Errorf("expected 0 new docs on second sync, got %d (resume failed)", len(docs2))
	}

	// Append two new commands and sync again — must return exactly those 2.
	appended := initial + "docker ps\ngit diff\n"
	os.WriteFile(path, []byte(appended), 0644)

	docs3, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("third sync failed: %v", err)
	}
	if len(docs3) != 2 {
		t.Errorf("expected 2 new docs on third sync, got %d", len(docs3))
	}
	if docs3[0].Snippet != "docker ps" {
		t.Errorf("expected first new doc snippet 'docker ps', got %q", docs3[0].Snippet)
	}
	if docs3[1].Snippet != "git diff" {
		t.Errorf("expected second new doc snippet 'git diff', got %q", docs3[1].Snippet)
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
