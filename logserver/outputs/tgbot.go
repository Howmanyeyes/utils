package outputs

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
)

type TGOutput struct {
	Level   int         `json:"level"`
	API_KEY string      `json:"API_KEY"`
	Chats   map[int]int `json:"chats"`
}

func (s *TGOutput) GetLevel() int {
	return s.Level
}

func (s *TGOutput) Process(log Log) error {
	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", s.API_KEY)

	for userID, level := range s.Chats {
		if level > log.Level {
			continue
		}
		payload := map[string]interface{}{
			"chat_id": userID,
			"text":    log.Msg,
		}
		jsonPayload, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("failed to marshal JSON payload: %w", err)
		}

		req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonPayload))
		if err != nil {
			return fmt.Errorf("failed to create HTTP request: %w", err)
		}
		req.Header.Set("Content-Type", "application/json")

		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			return fmt.Errorf("failed to send HTTP request: %w", err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return fmt.Errorf("received non-OK response from Telegram API: %d", resp.StatusCode)
		}
	}

	return nil

}
