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
	pendingUpdates := make(map[string]*state.SourceState)

	for _, src := range activeSources {
		log.Printf("Collecting from %s...", src.Name())
		sourceType := src.SourceType()
		srcState := cloneSourceState(st.GetSourceState(sourceType))
		docs, err := src.CollectNew(srcState)
		if err != nil {
			log.Printf("Error collecting from %s: %v", src.Name(), err)
			continue
		}
		log.Printf("Collected %d new documents from %s", len(docs), src.Name())
		allDocs = append(allDocs, docs...)
		if len(docs) == 0 {
			st.UpdateSourceState(sourceType, srcState)
			continue
		}
		pendingUpdates[sourceType] = srcState
	}

	if len(allDocs) == 0 {
		log.Printf("No new documents to index")
		if err := state.Save(cfg.StateFile, st); err != nil {
			log.Printf("Warning: could not save state: %v", err)
		}
		return nil
	}

	durable := false

	// Drain queue first, file by file so progress survives restarts
	queueErr := q.DrainFiles(func(docs []client.Document) error {
		return indexInBatches(c, docs)
	})
	if queueErr != nil {
		log.Printf("Error draining queue: %v, will retry on next sync", queueErr)
		// Queue new docs since server appears down
		if qErr := q.Enqueue(allDocs); qErr != nil {
			log.Printf("Error queuing new documents: %v", qErr)
		} else {
			durable = true
			applySourceStateUpdates(st, pendingUpdates)
		}
		if err := state.Save(cfg.StateFile, st); err != nil {
			log.Printf("Warning: could not save state: %v", err)
		}
		return nil
	}

	// Send new docs
	if err := indexInBatches(c, allDocs); err != nil {
		log.Printf("Server unavailable: %v, queuing %d documents", err, len(allDocs))
		if qErr := q.Enqueue(allDocs); qErr != nil {
			log.Printf("Error queuing documents: %v", qErr)
		} else {
			durable = true
		}
	} else {
		log.Printf("Successfully indexed %d documents", len(allDocs))
		durable = true
	}

	if durable {
		applySourceStateUpdates(st, pendingUpdates)
	}
	if err := state.Save(cfg.StateFile, st); err != nil {
		log.Printf("Warning: could not save state: %v", err)
	}
	return nil
}

const batchSize = 100
const maxContentBytes = 100_000

func indexInBatches(c *client.Client, docs []client.Document) error {
	for i := 0; i < len(docs); i += batchSize {
		end := i + batchSize
		if end > len(docs) {
			end = len(docs)
		}
		batch := make([]client.Document, end-i)
		for j, doc := range docs[i:end] {
			if len(doc.Content) > maxContentBytes {
				doc.Content = doc.Content[:maxContentBytes]
			}
			batch[j] = doc
		}
		log.Printf("Sending batch %d-%d of %d documents...", i+1, end, len(docs))
		if err := c.IndexDocuments(batch); err != nil {
			return err
		}
	}
	return nil
}

func cloneSourceState(src *state.SourceState) *state.SourceState {
	if src == nil {
		return &state.SourceState{}
	}
	clone := *src
	if src.LastLines != nil {
		clone.LastLines = append([]string(nil), src.LastLines...)
	}
	return &clone
}

func applySourceStateUpdates(st *state.State, updates map[string]*state.SourceState) {
	for sourceType, srcState := range updates {
		st.UpdateSourceState(sourceType, srcState)
	}
}
