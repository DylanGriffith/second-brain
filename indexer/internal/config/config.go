package config

import (
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Config struct {
	ServerURL string
	StateDir  string
	StateFile string
	QueueDir  string
	Interval  time.Duration
}

func New(serverURL, stateDir string) (*Config, error) {
	expanded := expandHome(stateDir)
	if err := os.MkdirAll(expanded, 0755); err != nil {
		return nil, err
	}
	queueDir := filepath.Join(expanded, "queue")
	if err := os.MkdirAll(queueDir, 0755); err != nil {
		return nil, err
	}
	return &Config{
		ServerURL: serverURL,
		StateDir:  expanded,
		StateFile: filepath.Join(expanded, "state.json"),
		QueueDir:  queueDir,
		Interval:  5 * time.Minute,
	}, nil
}

func expandHome(path string) string {
	if strings.HasPrefix(path, "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return path
		}
		return filepath.Join(home, path[2:])
	}
	return path
}
