package cmd

import (
	"fmt"

	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/DylanGriffith/second-brain/indexer/internal/queue"
	"github.com/DylanGriffith/second-brain/indexer/internal/sources"
	"github.com/DylanGriffith/second-brain/indexer/internal/state"
	"github.com/spf13/cobra"
)

var statusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show sync status and source availability",
	RunE:  runStatusCmd,
}

func init() {
	rootCmd.AddCommand(statusCmd)
}

func runStatusCmd(cmd *cobra.Command, args []string) error {
	cfg, err := config.New(serverURL, stateDir)
	if err != nil {
		return err
	}

	st, err := state.Load(cfg.StateFile)
	if err != nil {
		fmt.Println("No state found (never synced)")
		st = state.New()
	}

	q := queue.New(cfg.QueueDir)
	queueSize, _ := q.Size()

	fmt.Printf("Server: %s\n", cfg.ServerURL)
	fmt.Printf("State dir: %s\n", cfg.StateDir)
	fmt.Printf("Queued documents: %d\n", queueSize)
	fmt.Println()
	fmt.Println("Sources:")

	activeSources := sources.GetActiveSources(cfg)
	for _, src := range activeSources {
		srcState := st.GetSourceState(src.SourceType())
		available := "available"
		if !src.IsAvailable() {
			available = "unavailable"
		}
		lastSync := "never"
		if !srcState.LastSyncTime.IsZero() {
			lastSync = srcState.LastSyncTime.Format("2006-01-02 15:04:05")
		}
		fmt.Printf("  %-20s %-12s last sync: %s\n", src.Name(), available, lastSync)
	}
	return nil
}
