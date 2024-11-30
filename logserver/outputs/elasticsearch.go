package outputs

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type ElasticOutput struct {
	Level int    `json:"level"`
	Host  string `json:"host"`
	Index string `json:"index"`
}

func (s *ElasticOutput) GetLevel() int {
	return s.Level
}

var META = []string{"@timestamp", "FuncName", "LevelName", "message"}

// '%(asctime)s | %(funcName)s | %(levelname)s | %(message)s'
func (s *ElasticOutput) Parser(logmsg string) map[string]interface{} {
	parts := strings.Split(logmsg, "||")
	ans := make(map[string]interface{})
	if len(parts) == 0 {
		return ans
	}
	meta := strings.Split(parts[0], "|")
	for i, val := range meta {
		ans[META[i]] = strings.TrimSpace(val)
	}
	if len(parts) > 1 {
		data := strings.Split(parts[1], ";")
		for _, item := range data {
			kv := strings.SplitN(item, ": ", 2)
			if len(kv) == 2 {
				key := strings.TrimSpace(kv[0])
				value := strings.TrimSpace(kv[1])
				ans[key] = value
			}
		}
	}
	return ans
}

func (s *ElasticOutput) Process(log Log) error {
	url := fmt.Sprintf("%s/%s/_doc", s.Host, s.Index)

	// Marshal log to JSON
	//jsonPayload, err := json.Marshal(log)
	//if err != nil {
	//	return fmt.Errorf("failed to marshal log to JSON: %w", err)
	//}
	jsonik := s.Parser(log.Msg)
	jsonik["ip"] = log.IP
	jsonik["login"] = log.Login
	jsonik["level"] = log.Level
	jsonPayload, err := json.Marshal(jsonik)
	if err != nil {
		return fmt.Errorf("failed to marshal log to JSON: %w", err)
	}
	// Create a new HTTP POST request
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return fmt.Errorf("failed to create HTTP request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	// Execute HTTP request
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send HTTP request: %w", err)
	}
	// Check for successful response
	if resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("received non-OK response from Elasticsearch: %d", resp.StatusCode)
	}
	defer resp.Body.Close()

	// req, err := http.NewRequest("GET", "https://kibanaadmin:test@worker.agicotech.ru/", bytes.NewBuffer()) //, bytes.NewBuffer(jsonPayload))

	return nil
}
