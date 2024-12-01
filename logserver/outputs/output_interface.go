package outputs

import (
	"fmt"
	"strings"
)

type LogS struct {
	Level     int    `json:"level"`
	Message   string `json:"message"`
	Timestamp string `json:"timestamp"`
	FuncName  string `json:"funcName"`
	LevelName string `json:"levelName"`
	Login     string
	Extras    map[string]interface{} `lson:"extras"`
}

type Output interface {
	Process(log LogS) error
	GetLevel() int
}

func mapToString(data map[string]interface{}) string {
	// Use a strings.Builder for efficient string concatenation
	var builder strings.Builder

	// Iterate over the map
	first := true
	for key, value := range data {
		// Add a comma before appending the next pair unless it's the first pair
		if !first {
			builder.WriteString(", ")
		}
		first = false

		// Write the "key : value" pair to the builder
		builder.WriteString(fmt.Sprintf("%s : %v", key, value))
	}

	// Return the final constructed string
	return builder.String()
}

func (l *LogS) StrFmt() string {
	s := fmt.Sprintf("%s >> %s | %s | %s | %s", l.Login, l.Timestamp, l.FuncName, l.LevelName, l.Message)
	if len(l.Extras) > 0 {
		s = fmt.Sprintf("%s || %s", s, mapToString(l.Extras))
	}
	return s
}
