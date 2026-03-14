package sources

import (
	"crypto/sha256"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

type PsqlSource struct {
	historyPath string
}

func NewPsqlSource(cfg *config.Config) *PsqlSource {
	home, _ := os.UserHomeDir()
	return &PsqlSource{
		historyPath: filepath.Join(home, ".psql_history"),
	}
}

func NewPsqlSourceWithPath(path string) *PsqlSource {
	return &PsqlSource{historyPath: path}
}

func (s *PsqlSource) Name() string       { return "Psql History" }
func (s *PsqlSource) SourceType() string { return "psql_history" }
func (s *PsqlSource) IsAvailable() bool {
	_, err := os.Stat(s.historyPath)
	return err == nil
}

func (s *PsqlSource) CollectNew(srcState *state.SourceState) ([]client.Document, error) {
	data, err := os.ReadFile(s.historyPath)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(s.historyPath)
	if err != nil {
		return nil, err
	}
	lastSeen := info.ModTime().UnixMilli()

	// Normalize upfront: trim whitespace and drop empty lines (same as bash source).
	var allLines []string
	for _, l := range strings.Split(string(data), "\n") {
		if t := strings.TrimSpace(l); t != "" {
			allLines = append(allLines, t)
		}
	}
	startIdx := findResumePoint(allLines, srcState.LastLines)
	newLines := allLines[startIdx:]

	var docs []client.Document
	var lastTen []string

	for _, line := range newLines {
		// Replace \n literals with actual newlines for multi-line SQL
		fullSQL := strings.ReplaceAll(line, "\\n", "\n")
		hash := sha256.Sum256([]byte(line))
		globalID := fmt.Sprintf("psql_history:%x", hash[:8])
		title := fullSQL
		if len(title) > 50 {
			title = title[:50]
		}
		docs = append(docs, client.Document{
			GlobalID: globalID,
			Title:    title,
			Domain:   "psql",
			Snippet:  fullSQL,
			LastSeen: lastSeen,
		})
		lastTen = append(lastTen, line)
		if len(lastTen) > 10 {
			lastTen = lastTen[len(lastTen)-10:]
		}
	}

	if len(lastTen) > 0 {
		srcState.LastLines = lastTen
	}
	log.Printf("Psql: collected %d new queries", len(docs))
	return docs, nil
}
