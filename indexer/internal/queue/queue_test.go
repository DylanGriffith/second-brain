package queue_test

import (
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/queue"
)

func TestQueueEnqueueAndLoad(t *testing.T) {
	tmp := t.TempDir()
	q := queue.New(tmp)

	docs := []client.Document{
		{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "snippet", LastSeen: 1000},
		{GlobalID: "test:2", Title: "Doc 2", Domain: "test", Snippet: "snippet", LastSeen: 2000},
	}

	if err := q.Enqueue(docs); err != nil {
		t.Fatalf("enqueue failed: %v", err)
	}

	loaded, err := q.LoadAll()
	if err != nil {
		t.Fatalf("load failed: %v", err)
	}
	if len(loaded) != 2 {
		t.Errorf("expected 2 docs, got %d", len(loaded))
	}
}

func TestQueueClearAll(t *testing.T) {
	tmp := t.TempDir()
	q := queue.New(tmp)

	docs := []client.Document{{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "s", LastSeen: 1000}}
	q.Enqueue(docs)

	q.ClearAll()

	loaded, _ := q.LoadAll()
	if len(loaded) != 0 {
		t.Errorf("expected 0 docs after clear, got %d", len(loaded))
	}
}

func TestQueueSize(t *testing.T) {
	tmp := t.TempDir()
	q := queue.New(tmp)

	size, _ := q.Size()
	if size != 0 {
		t.Errorf("expected 0 size, got %d", size)
	}

	docs := []client.Document{{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "s", LastSeen: 1000}}
	q.Enqueue(docs)

	size, _ = q.Size()
	if size != 1 {
		t.Errorf("expected 1 size, got %d", size)
	}
}
