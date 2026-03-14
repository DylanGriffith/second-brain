package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Document struct {
	GlobalID string `json:"global_id"`
	Title    string `json:"title"`
	Domain   string `json:"domain"`
	Snippet  string `json:"snippet"`
	LastSeen int64  `json:"last_seen"`
	URL      string `json:"url,omitempty"`
	Content  string `json:"content,omitempty"`
}

type indexRequest struct {
	Documents []Document `json:"documents"`
}

type indexResponse struct {
	Indexed int `json:"indexed"`
	Errors  int `json:"errors"`
}

type Client struct {
	serverURL  string
	httpClient *http.Client
}

func New(serverURL string) *Client {
	return &Client{
		serverURL: serverURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) IndexDocuments(docs []Document) error {
	if len(docs) == 0 {
		return nil
	}
	req := indexRequest{Documents: docs}
	body, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("marshal error: %w", err)
	}
	resp, err := c.httpClient.Post(
		c.serverURL+"/api/v1/documents",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return fmt.Errorf("server returned %d", resp.StatusCode)
	}
	var result indexResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("decode error: %w", err)
	}
	if result.Errors > 0 {
		return fmt.Errorf("server reported %d errors indexing documents", result.Errors)
	}
	return nil
}
