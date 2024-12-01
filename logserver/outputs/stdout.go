package outputs

import (
	"fmt"
)

type StdoutOutput struct {
	Level int `json:"level"`
}

func (s *StdoutOutput) Process(log LogS) error {
	if log.Level >= s.Level {
		fmt.Println(log.StrFmt())
	}
	return nil
}

func (s *StdoutOutput) GetLevel() int {
	return s.Level
}
