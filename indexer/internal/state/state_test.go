package state_test

import (
	"path/filepath"
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

func TestStateSaveLoad(t *testing.T) {
	tmp := t.TempDir()
	path := filepath.Join(tmp, "state.json")

	s := state.New()
	ss := s.GetSourceState("bash_history")
	ss.LastLines = []string{"ls", "cd ~", "git status"}
	s.UpdateSourceState("bash_history", ss)

	if err := state.Save(path, s); err != nil {
		t.Fatalf("save failed: %v", err)
	}

	s2, err := state.Load(path)
	if err != nil {
		t.Fatalf("load failed: %v", err)
	}

	ss2 := s2.GetSourceState("bash_history")
	if len(ss2.LastLines) != 3 {
		t.Errorf("expected 3 lines, got %d", len(ss2.LastLines))
	}
	if ss2.LastLines[0] != "ls" {
		t.Errorf("wrong line: %s", ss2.LastLines[0])
	}
}

func TestStateMissingFile(t *testing.T) {
	_, err := state.Load("/nonexistent/path/state.json")
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestStateGetSourceStateCreatesNew(t *testing.T) {
	s := state.New()
	ss := s.GetSourceState("nonexistent")
	if ss == nil {
		t.Fatal("expected non-nil SourceState")
	}
	if !ss.LastSyncTime.IsZero() {
		t.Error("expected zero LastSyncTime for new state")
	}
}
