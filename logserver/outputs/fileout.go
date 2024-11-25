package outputs

import (
	"os"
)

type FileOutput struct {
	Level int    `json:"level"`
	Path  string `json:"path"`
}

func (s *FileOutput) Process(log Log) error {
	if log.Level >= s.Level {
		f, err := os.OpenFile(s.Path, os.O_APPEND|os.O_WRONLY|os.O_CREATE, 0600)
		if err != nil {
			return err
		}
		defer f.Close()
		if _, err = f.WriteString(log.Msg + "\n"); err != nil {
			return err
		}
	}
	return nil
}

func (s *FileOutput) GetLevel() int {
	return s.Level
}
