package sources_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/DylanGriffith/second-brain/indexer/internal/sources"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

func TestNeovimCollectNew_Basic(t *testing.T) {
	tmp := t.TempDir()
	// Create a real text file to track
	textFile := filepath.Join(tmp, "main.go")
	os.WriteFile(textFile, []byte("package main\n"), 0644)

	logPath := filepath.Join(tmp, "neovim.log")
	ts := time.Now().Format("2006-01-02T15:04:05")
	os.WriteFile(logPath, []byte(ts+" "+textFile+"\n"), 0644)

	src := sources.NewNeovimSourceWithPath(logPath)
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) != 1 {
		t.Fatalf("expected 1 doc, got %d", len(docs))
	}
	if docs[0].GlobalID != "neovim:"+textFile {
		t.Errorf("wrong global_id: %s", docs[0].GlobalID)
	}
	if docs[0].Title != "main.go" {
		t.Errorf("wrong title: %s", docs[0].Title)
	}
}

func TestNeovimCollectNew_SkipsBinary(t *testing.T) {
	tmp := t.TempDir()
	binFile := filepath.Join(tmp, "binary.bin")
	os.WriteFile(binFile, []byte{0x00, 0x01, 0x02, 0x03}, 0644)

	logPath := filepath.Join(tmp, "neovim.log")
	ts := time.Now().Format("2006-01-02T15:04:05")
	os.WriteFile(logPath, []byte(ts+" "+binFile+"\n"), 0644)

	src := sources.NewNeovimSourceWithPath(logPath)
	st := &state.SourceState{}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	if len(docs) != 0 {
		t.Errorf("expected 0 docs (binary), got %d", len(docs))
	}
}

func TestNeovimCollectNew_CursorResume(t *testing.T) {
	tmp := t.TempDir()
	textFile := filepath.Join(tmp, "file.txt")
	os.WriteFile(textFile, []byte("hello"), 0644)

	logPath := filepath.Join(tmp, "neovim.log")
	old := "2020-01-01T00:00:00"
	newTS := time.Now().Format("2006-01-02T15:04:05")
	content := old + " " + textFile + "\n" + newTS + " " + textFile + "\n"
	os.WriteFile(logPath, []byte(content), 0644)

	src := sources.NewNeovimSourceWithPath(logPath)
	st := &state.SourceState{Cursor: "2021-01-01T00:00:00"}
	docs, err := src.CollectNew(st)
	if err != nil {
		t.Fatalf("CollectNew failed: %v", err)
	}
	// Only the new entry should be collected
	if len(docs) != 1 {
		t.Errorf("expected 1 doc (cursor filter), got %d", len(docs))
	}
}
