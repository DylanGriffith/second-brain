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

type BashSource struct {
	historyPath string
}

func NewBashSource(cfg *config.Config) *BashSource {
	home, _ := os.UserHomeDir()
	return &BashSource{
		historyPath: filepath.Join(home, ".bash_history"),
	}
}

func NewBashSourceWithPath(path string) *BashSource {
	return &BashSource{historyPath: path}
}

func (s *BashSource) Name() string       { return "Bash History" }
func (s *BashSource) SourceType() string { return "bash_history" }
func (s *BashSource) IsAvailable() bool {
	_, err := os.Stat(s.historyPath)
	return err == nil
}

func (s *BashSource) CollectNew(srcState *state.SourceState) ([]client.Document, error) {
	data, err := os.ReadFile(s.historyPath)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(s.historyPath)
	if err != nil {
		return nil, err
	}
	lastSeen := info.ModTime().UnixMilli()

	allLines := strings.Split(strings.TrimRight(string(data), "\n"), "\n")

	startIdx := findResumePoint(allLines, srcState.LastLines)
	newLines := allLines[startIdx:]

	hostname, _ := os.Hostname()

	var docs []client.Document
	var lastTen []string

	for _, line := range newLines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		hash := sha256.Sum256([]byte(line))
		globalID := fmt.Sprintf("bash_history:%x", hash[:8])
		title := line
		if len(title) > 50 {
			title = title[:50]
		}
		docs = append(docs, client.Document{
			GlobalID: globalID,
			Title:    title,
			Domain:   hostname,
			Snippet:  line,
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
	log.Printf("Bash: collected %d new commands", len(docs))
	return docs, nil
}

func findResumePoint(allLines []string, lastLines []string) int {
	if len(lastLines) == 0 {
		return 0
	}
	// Search from end for the last known lines
	for i := len(allLines) - 1; i >= 0; i-- {
		// Try to match lastLines ending at position i
		if matchesAt(allLines, i, lastLines) {
			return i + 1
		}
	}
	return 0 // not found, re-sync all
}

func matchesAt(allLines []string, endIdx int, lastLines []string) bool {
	startIdx := endIdx - len(lastLines) + 1
	if startIdx < 0 {
		return false
	}
	for j, line := range lastLines {
		if allLines[startIdx+j] != line {
			return false
		}
	}
	return true
}
