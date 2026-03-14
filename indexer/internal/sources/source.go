package sources

import (
	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
)

type Source interface {
	Name() string
	SourceType() string
	IsAvailable() bool
	CollectNew(srcState *state.SourceState) ([]client.Document, error)
}

func GetActiveSources(cfg *config.Config) []Source {
	all := []Source{
		NewBashSource(cfg),
		NewPsqlSource(cfg),
		NewChromeSource(cfg),
		NewNeovimSource(cfg),
	}
	var active []Source
	for _, s := range all {
		if s.IsAvailable() {
			active = append(active, s)
		}
	}
	return active
}
