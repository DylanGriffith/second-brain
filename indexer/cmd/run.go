package cmd

import (
	"fmt"
	"log"
	"time"

	"github.com/DylanGriffith/second-brain/indexer/internal/config"
	"github.com/spf13/cobra"
)

var runCmd = &cobra.Command{
	Use:   "run",
	Short: "Start background daemon mode",
	RunE:  runDaemonCmd,
}

func init() {
	rootCmd.AddCommand(runCmd)
}

func runDaemonCmd(cmd *cobra.Command, args []string) error {
	cfg, err := config.New(serverURL, stateDir)
	if err != nil {
		return err
	}

	intervalDur, err := time.ParseDuration(interval)
	if err != nil {
		return fmt.Errorf("invalid interval %q: %w", interval, err)
	}
	cfg.Interval = intervalDur

	log.Printf("Starting daemon with interval %s", cfg.Interval)
	for {
		log.Printf("Running sync...")
		if err := RunSync(cfg); err != nil {
			log.Printf("Sync error: %v", err)
		}
		log.Printf("Next sync in %s", cfg.Interval)
		time.Sleep(cfg.Interval)
	}
}
