package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	serverURL string
	stateDir  string
	interval  string
)

var rootCmd = &cobra.Command{
	Use:   "sb",
	Short: "Second Brain - personal knowledge indexer",
	Long:  "sb collects data from local sources and indexes it to the second-brain server",
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.PersistentFlags().StringVar(&serverURL, "server-url", "http://localhost:8000", "Python server URL")
	rootCmd.PersistentFlags().StringVar(&stateDir, "state-dir", "~/.second-brain/", "State directory")
	rootCmd.PersistentFlags().StringVar(&interval, "interval", "5m", "Sync interval for daemon mode")
}
