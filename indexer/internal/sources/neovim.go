package sources

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

type NeovimSource struct {
	logPath string
}

func NewNeovimSource(cfg *config.Config) *NeovimSource {
	return &NeovimSource{
		logPath: filepath.Join(cfg.StateDir, "neovim-opened-files.log"),
	}
}

func NewNeovimSourceWithPath(path string) *NeovimSource {
	return &NeovimSource{logPath: path}
}

func (s *NeovimSource) Name() string       { return "Neovim Files" }
func (s *NeovimSource) SourceType() string { return "neovim_files" }
func (s *NeovimSource) IsAvailable() bool {
	_, err := os.Stat(s.logPath)
	return err == nil
}

func (s *NeovimSource) CollectNew(srcState *state.SourceState) ([]client.Document, error) {
	f, err := os.Open(s.logPath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var cursorTime time.Time
	if srcState.Cursor != "" {
		cursorTime, _ = time.Parse("2006-01-02T15:04:05", srcState.Cursor)
	}

	hostname, _ := os.Hostname()
	var docs []client.Document
	var lastTimestamp string
	seen := make(map[string]bool) // dedup by filepath

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, " ", 2)
		if len(parts) != 2 {
			continue
		}
		tsStr, fpath := parts[0], parts[1]
		ts, err := time.Parse("2006-01-02T15:04:05", tsStr)
		if err != nil {
			continue
		}
		if !cursorTime.IsZero() && !ts.After(cursorTime) {
			continue
		}
		lastTimestamp = tsStr

		if seen[fpath] {
			continue
		}
		seen[fpath] = true

		info, err := os.Stat(fpath)
		if err != nil {
			continue
		}
		if info.IsDir() {
			continue
		}

		content, err := readTextFile(fpath)
		if err != nil {
			continue // binary or unreadable
		}
		if len(content) > 10000 {
			content = content[:10000]
		}

		docs = append(docs, client.Document{
			GlobalID: fmt.Sprintf("neovim:%s", fpath),
			Title:    filepath.Base(fpath),
			Domain:   hostname,
			Snippet:  fpath,
			LastSeen: info.ModTime().UnixMilli(),
			Content:  content,
		})
	}

	if lastTimestamp != "" {
		srcState.Cursor = lastTimestamp
	}
	log.Printf("Neovim: collected %d files", len(docs))
	return docs, nil
}

func readTextFile(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	// Check for binary content (null bytes)
	for _, b := range data {
		if b == 0 {
			return "", fmt.Errorf("binary file")
		}
	}
	return string(data), nil
}
