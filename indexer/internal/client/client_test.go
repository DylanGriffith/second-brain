package client_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
)

func TestClientIndexDocuments_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/documents" {
			t.Errorf("wrong path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]int{"indexed": 2, "errors": 0})
	}))
	defer server.Close()

	c := client.New(server.URL)
	docs := []client.Document{
		{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "s", LastSeen: 1000},
		{GlobalID: "test:2", Title: "Doc 2", Domain: "test", Snippet: "s", LastSeen: 2000},
	}

	if err := c.IndexDocuments(docs); err != nil {
		t.Fatalf("IndexDocuments failed: %v", err)
	}
}

func TestClientIndexDocuments_ServerError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	c := client.New(server.URL)
	docs := []client.Document{{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "s", LastSeen: 1000}}

	err := c.IndexDocuments(docs)
	if err == nil {
		t.Fatal("expected error for server error response")
	}
}

func TestClientIndexDocuments_ConnectionRefused(t *testing.T) {
	c := client.New("http://localhost:1") // nothing listening
	docs := []client.Document{{GlobalID: "test:1", Title: "Doc 1", Domain: "test", Snippet: "s", LastSeen: 1000}}

	err := c.IndexDocuments(docs)
	if err == nil {
		t.Fatal("expected error for connection refused")
	}
}

func TestClientIndexDocuments_Empty(t *testing.T) {
	c := client.New("http://localhost:1")
	// Empty docs should return nil without making a request
	err := c.IndexDocuments(nil)
	if err != nil {
		t.Fatalf("unexpected error for empty docs: %v", err)
	}
}
