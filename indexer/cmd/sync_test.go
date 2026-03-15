package cmd

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/queue"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

func TestRunSync_DoesNotAdvanceStateWhenIndexAndQueueFail(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	historyPath := filepath.Join(home, ".bash_history")
	if err := os.WriteFile(historyPath, []byte("git status\n"), 0644); err != nil {
		t.Fatalf("write history: %v", err)
	}

	stateDir := t.TempDir()
	queueBlocker := filepath.Join(stateDir, "queue-blocker")
	if err := os.WriteFile(queueBlocker, []byte("not a directory"), 0644); err != nil {
		t.Fatalf("write queue blocker: %v", err)
	}

	cfg := &config.Config{
		ServerURL: "http://127.0.0.1:1",
		StateDir:  stateDir,
		StateFile: filepath.Join(stateDir, "state.json"),
		QueueDir:  queueBlocker,
	}

	if err := RunSync(cfg); err != nil {
		t.Fatalf("RunSync failed: %v", err)
	}

	st, err := state.Load(cfg.StateFile)
	if err != nil {
		t.Fatalf("load state: %v", err)
	}

	srcState, ok := st.Sources["bash_history"]
	if ok && (len(srcState.LastLines) > 0 || srcState.Cursor != "" || !srcState.LastSyncTime.IsZero()) {
		t.Fatalf("state advanced despite non-durable sync: %+v", *srcState)
	}
}

func TestRunSync_AdvancesStateWhenDocumentsAreQueued(t *testing.T) {
	home := t.TempDir()
	t.Setenv("HOME", home)

	historyPath := filepath.Join(home, ".bash_history")
	if err := os.WriteFile(historyPath, []byte("git status\n"), 0644); err != nil {
		t.Fatalf("write history: %v", err)
	}

	stateDir := t.TempDir()
	queueDir := filepath.Join(stateDir, "queue")
	if err := os.MkdirAll(queueDir, 0755); err != nil {
		t.Fatalf("mkdir queue dir: %v", err)
	}

	cfg := &config.Config{
		ServerURL: "http://127.0.0.1:1",
		StateDir:  stateDir,
		StateFile: filepath.Join(stateDir, "state.json"),
		QueueDir:  queueDir,
	}

	if err := RunSync(cfg); err != nil {
		t.Fatalf("RunSync failed: %v", err)
	}

	st, err := state.Load(cfg.StateFile)
	if err != nil {
		t.Fatalf("load state: %v", err)
	}

	srcState := st.GetSourceState("bash_history")
	if len(srcState.LastLines) != 1 || srcState.LastLines[0] != "git status" {
		t.Fatalf("expected state to advance after durable queue, got %+v", *srcState)
	}
	if srcState.LastSyncTime.IsZero() {
		t.Fatalf("expected last sync time to be recorded after durable queue")
	}

	q := queue.New(queueDir)
	size, err := q.Size()
	if err != nil {
		t.Fatalf("queue size: %v", err)
	}
	if size != 1 {
		t.Fatalf("expected 1 queued document, got %d", size)
	}
}
