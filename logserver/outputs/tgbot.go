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
	Topics  []TGTopic   `json:"topics"`
}

type TGTopic struct {
	ChatID          int `json:"chat_id"`
	MessageThreadID int `json:"message_thread_id"`
	Level           int `json:"level"`
}

func (s *TGOutput) GetLevel() int {
	return s.Level
}

func (s *TGOutput) Process(log LogS) error {
	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", s.API_KEY)

	for userID, level := range s.Chats {
		if level > log.Level {
			continue
		}
		if err := s.send(url, userID, nil, log); err != nil {
			return err
		}
	}

	for _, topic := range s.Topics {
		if topic.Level > log.Level {
			continue
		}
		threadID := topic.MessageThreadID
		if err := s.send(url, topic.ChatID, &threadID, log); err != nil {
			return err
		}
	}

	return nil

}

func (s *TGOutput) send(url string, chatID int, threadID *int, log LogS) error {
	payload := map[string]interface{}{
		"chat_id": chatID,
		"text":    log.StrFmt(),
	}
	if threadID != nil {
		payload["message_thread_id"] = *threadID
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

	return nil
}
