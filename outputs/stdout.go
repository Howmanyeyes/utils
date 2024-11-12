package outputs

import (
	"fmt"
)

type StdoutOutput struct {
	Level int `json:"level"`
}

func (s *StdoutOutput) Process(log Log) error {
	if log.Level >= s.Level {
		fmt.Printf("Received log: %+v\n", log)
	}
	return nil
}

func (s *StdoutOutput) GetLevel() int {
	return s.Level
}
