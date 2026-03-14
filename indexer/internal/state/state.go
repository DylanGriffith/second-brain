package state

import (
	"encoding/json"
	"os"
	"time"
)

type SourceState struct {
	LastSyncTime time.Time `json:"last_sync_time"`
	LastLines    []string  `json:"last_lines,omitempty"` // for bash/psql history resume
	Cursor       string    `json:"cursor,omitempty"`     // for chrome/neovim cursor-based resume
}

type State struct {
	Sources map[string]*SourceState `json:"sources"`
}

func New() *State {
	return &State{Sources: make(map[string]*SourceState)}
}

func Load(path string) (*State, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var s State
	if err := json.Unmarshal(data, &s); err != nil {
		return nil, err
	}
	if s.Sources == nil {
		s.Sources = make(map[string]*SourceState)
	}
	return &s, nil
}

func Save(path string, s *State) error {
	data, err := json.MarshalIndent(s, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (s *State) GetSourceState(sourceType string) *SourceState {
	if ss, ok := s.Sources[sourceType]; ok {
		return ss
	}
	ss := &SourceState{}
	s.Sources[sourceType] = ss
	return ss
}

func (s *State) UpdateSourceState(sourceType string, ss *SourceState) {
	ss.LastSyncTime = time.Now()
	s.Sources[sourceType] = ss
}
