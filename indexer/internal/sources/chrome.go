package sources

import (
	"database/sql"
	"fmt"
	"io"
	"log"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"time"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
	_ "github.com/mattn/go-sqlite3"
)

type ChromeSource struct {
	historyPath string
}

func NewChromeSource(cfg *config.Config) *ChromeSource {
	return &ChromeSource{
		historyPath: defaultChromeHistoryPath(),
	}
}

func NewChromeSourceWithPath(path string) *ChromeSource {
	return &ChromeSource{
		historyPath: path,
	}
}

func defaultChromeHistoryPath() string {
	home, _ := os.UserHomeDir()
	if runtime.GOOS == "darwin" {
		return filepath.Join(home, "Library", "Application Support", "Google", "Chrome", "Default", "History")
	}
	return filepath.Join(home, ".config", "google-chrome", "Default", "History")
}

func (s *ChromeSource) Name() string       { return "Chrome History" }
func (s *ChromeSource) SourceType() string { return "chrome_history" }
func (s *ChromeSource) IsAvailable() bool {
	_, err := os.Stat(s.historyPath)
	return err == nil
}

func (s *ChromeSource) CollectNew(srcState *state.SourceState) ([]client.Document, error) {
	// Copy to temp file to avoid locking
	tmp, err := os.CreateTemp("", "chrome-history-*.db")
	if err != nil {
		return nil, err
	}
	defer os.Remove(tmp.Name())
	tmp.Close()

	src, err := os.Open(s.historyPath)
	if err != nil {
		return nil, err
	}
	dst, err := os.Create(tmp.Name())
	if err != nil {
		src.Close()
		return nil, err
	}
	_, err = io.Copy(dst, src)
	src.Close()
	dst.Close()
	if err != nil {
		return nil, err
	}

	db, err := sql.Open("sqlite3", tmp.Name()+"?mode=ro")
	if err != nil {
		return nil, err
	}
	defer db.Close()

	cursor, _ := strconv.ParseInt(srcState.Cursor, 10, 64)
	const chromeEpochOffset = 11644473600
	oneMonthAgo := (time.Now().AddDate(0, -1, 0).Unix() + chromeEpochOffset) * 1000000
	if oneMonthAgo > cursor {
		cursor = oneMonthAgo
	}
	rows, err := db.Query(
		"SELECT url, title, last_visit_time FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time ASC",
		cursor,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var docs []client.Document
	var maxCursor int64

	for rows.Next() {
		var rawURL, title string
		var lastVisitTime int64
		if err := rows.Scan(&rawURL, &title, &lastVisitTime); err != nil {
			continue
		}
		if lastVisitTime > maxCursor {
			maxCursor = lastVisitTime
		}
		lastSeen := ((lastVisitTime / 1000000) - chromeEpochOffset) * 1000

		domain := extractDomain(rawURL)
		if title == "" {
			title = rawURL
		}

		docs = append(docs, client.Document{
			GlobalID: fmt.Sprintf("chrome_history:%s", rawURL),
			Title:    title,
			Domain:   domain,
			Snippet:  title,
			LastSeen: lastSeen,
			URL:      rawURL,
		})
	}

	if maxCursor > 0 {
		srcState.Cursor = strconv.FormatInt(maxCursor, 10)
	}
	log.Printf("Chrome: collected %d new URLs", len(docs))
	return docs, nil
}

func extractDomain(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil {
		return "unknown"
	}
	return u.Hostname()
}
