package queue

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/DylanGriffith/second-brain/indexer/internal/client"
)

type Queue struct {
	dir string
}

func New(dir string) *Queue {
	return &Queue{dir: dir}
}

func (q *Queue) Enqueue(docs []client.Document) error {
	filename := fmt.Sprintf("queue-%d.json", time.Now().UnixNano())
	path := filepath.Join(q.dir, filename)
	data, err := json.Marshal(docs)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func (q *Queue) LoadAll() ([]client.Document, error) {
	entries, err := os.ReadDir(q.dir)
	if err != nil {
		return nil, err
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() && len(e.Name()) > 6 && e.Name()[:6] == "queue-" {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)

	var all []client.Document
	for _, f := range files {
		data, err := os.ReadFile(filepath.Join(q.dir, f))
		if err != nil {
			continue
		}
		var docs []client.Document
		if err := json.Unmarshal(data, &docs); err != nil {
			continue
		}
		all = append(all, docs...)
	}
	return all, nil
}

func (q *Queue) ClearAll() {
	entries, _ := os.ReadDir(q.dir)
	for _, e := range entries {
		if !e.IsDir() && len(e.Name()) > 6 && e.Name()[:6] == "queue-" {
			os.Remove(filepath.Join(q.dir, e.Name()))
		}
	}
}

// DrainFiles processes queue files one at a time, deleting each after process() succeeds.
// If process() returns an error, draining stops and the remaining files are left intact.
func (q *Queue) DrainFiles(process func([]client.Document) error) error {
	entries, err := os.ReadDir(q.dir)
	if err != nil {
		return err
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() && len(e.Name()) > 6 && e.Name()[:6] == "queue-" {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)

	for _, f := range files {
		path := filepath.Join(q.dir, f)
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		var docs []client.Document
		if err := json.Unmarshal(data, &docs); err != nil {
			continue
		}
		if err := process(docs); err != nil {
			return err
		}
		os.Remove(path)
	}
	return nil
}

func (q *Queue) Size() (int, error) {
	docs, err := q.LoadAll()
	return len(docs), err
}
