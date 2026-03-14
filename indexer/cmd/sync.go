package cmd

import (
	"log"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/queue"
	"github.com/DylanGriffith/second-brain/indexer/internal/sources"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
	"github.com/spf13/cobra"
)

var syncCmd = &cobra.Command{
	Use:   "sync",
	Short: "One-shot: collect and send data to server",
	RunE:  runSyncCmd,
}

func init() {
	rootCmd.AddCommand(syncCmd)
}

func runSyncCmd(cmd *cobra.Command, args []string) error {
	cfg, err := config.New(serverURL, stateDir)
	if err != nil {
		return err
	}
	return RunSync(cfg)
}

func RunSync(cfg *config.Config) error {
	st, err := state.Load(cfg.StateFile)
	if err != nil {
		log.Printf("Warning: could not load state: %v, starting fresh", err)
		st = state.New()
	}

	c := client.New(cfg.ServerURL)
	q := queue.New(cfg.QueueDir)

	activeSources := sources.GetActiveSources(cfg)

	var allDocs []client.Document

	for _, src := range activeSources {
		log.Printf("Collecting from %s...", src.Name())
		srcState := st.GetSourceState(src.SourceType())
		docs, err := src.CollectNew(srcState)
		if err != nil {
			log.Printf("Error collecting from %s: %v", src.Name(), err)
			continue
		}
		log.Printf("Collected %d new documents from %s", len(docs), src.Name())
		allDocs = append(allDocs, docs...)
		st.UpdateSourceState(src.SourceType(), srcState)
	}

	if len(allDocs) == 0 {
		log.Printf("No new documents to index")
		if err := state.Save(cfg.StateFile, st); err != nil {
			log.Printf("Warning: could not save state: %v", err)
		}
		return nil
	}

	// Drain queue first
	if queued, err := q.LoadAll(); err == nil && len(queued) > 0 {
		log.Printf("Sending %d queued documents...", len(queued))
		if err := c.IndexDocuments(queued); err != nil {
			log.Printf("Error sending queued documents: %v, re-queuing", err)
			// Queue new docs too since server is down
			if qErr := q.Enqueue(allDocs); qErr != nil {
				log.Printf("Error queuing new documents: %v", qErr)
			}
			if err := state.Save(cfg.StateFile, st); err != nil {
				log.Printf("Warning: could not save state: %v", err)
			}
			return nil
		}
		q.ClearAll()
	}

	// Send new docs
	if err := c.IndexDocuments(allDocs); err != nil {
		log.Printf("Server unavailable: %v, queuing %d documents", err, len(allDocs))
		if qErr := q.Enqueue(allDocs); qErr != nil {
			log.Printf("Error queuing documents: %v", qErr)
		}
	} else {
		log.Printf("Successfully indexed %d documents", len(allDocs))
	}

	if err := state.Save(cfg.StateFile, st); err != nil {
		log.Printf("Warning: could not save state: %v", err)
	}
	return nil
}
