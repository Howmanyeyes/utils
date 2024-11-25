package main

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"logserver/outputs"
	"math"
	"net/http"
	"os"
	"sync"

	"github.com/gorilla/websocket"
	"gopkg.in/yaml.v2"
)

func convertMap(input map[interface{}]interface{}) (map[int]int, error) {
	result := make(map[int]int)

	for key, value := range input {
		intKey, okKey := key.(int)
		intValue, okValue := value.(int)

		if !okKey || !okValue {
			return nil, fmt.Errorf("key or value could not be converted to int")
		}

		result[intKey] = intValue
	}

	return result, nil
}

func minMapValue(m map[int]int) (int, int) {
	if len(m) == 0 {
		return -1, 0
	}

	minKey := -1
	minValue := math.MaxInt

	for key, value := range m {
		if value < minValue {
			minKey = key
			minValue = value
		}
	}

	return minKey, minValue
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

// Config structure
type Config struct {
	Port          string                   `yaml:"port"`
	WebSocketPath string                   `yaml:"websocket_path"`
	Users         []User                   `yaml:"users"`
	Outputs       []map[string]interface{} `yaml:"outputs"`
}

// User structure
type User struct {
	Username string `yaml:"username"`
	Password string `yaml:"password"`
}

// Log structure

// Abstract Output

// StdoutOutput class

// curl -u login:pass -X GET url

// Global Outputs
var Outputs []outputs.Output
var config Config
var usersMap = make(map[string]string)

var LogQueue = make(chan *outputs.Log, 1000)

// Add output to the list
func addOutput(output outputs.Output) {
	Outputs = append(Outputs, output)
}

// Handle WebSocket connection
func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		log.Println("No auth header received")
		return
	}

	username, ok := usersMap[authHeader]
	if !ok {
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
		log.Println("Unknown credentials")
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("Could not open websocket connection:", err)
		return
	}
	defer conn.Close()

	ip := r.RemoteAddr
	log.Println("!> Client connected ", ip)

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsCloseError(err) || websocket.IsUnexpectedCloseError(err) {
				log.Println("!> Client quitted", ip, err)
				return
			}
			log.Println("Error reading message:", err)
			break
		}

		var logData map[string]interface{}
		if err := json.Unmarshal(message, &logData); err != nil {
			log.Println("Invalid JSON format:", err)
			continue
		}

		logM := outputs.Log{
			Level: 20,
			IP:    ip,
			Login: username,
		}

		// Ensure log level field exists
		if level, ok := logData["level"].(float64); ok {
			logM.Level = int(level)
		}

		// Ensure msg field exists
		if msg, ok := logData["msg"].(string); ok {
			logM.Msg = msg
		}
		select {
		case LogQueue <- &logM:
			// Data enqueued successfully
		default:
			// Channel is full, handle accordingly
			log.Println("Log channel is full, discarding data!")
		}
		//processLog(log)
	}
}

// Process the log with each output
func processLog(log *outputs.Log) {
	var wg sync.WaitGroup
	for _, output := range Outputs {
		if log.Level >= output.GetLevel() {
			wg.Add(1)
			go func(out outputs.Output) {
				defer wg.Done()
				out.Process(*log)
			}(output)
		}
	}
	wg.Wait()
}

func loadConfig(configFile string) error {
	file, err := os.Open(configFile)
	if err != nil {
		return err
	}
	defer file.Close()

	decoder := yaml.NewDecoder(file)
	if err := decoder.Decode(&config); err != nil {
		return err
	}

	// Populate users map for faster lookup
	for _, user := range config.Users {
		hash := md5.Sum([]byte(user.Username + ":" + user.Password))
		hashedCredentials := hex.EncodeToString(hash[:])
		usersMap[hashedCredentials] = user.Username
	}

	return nil
}

func main() {
	// Load configuration
	if err := loadConfig("config.yaml"); err != nil {
		log.Fatalf("Error loading configuration: %v", err)
	}

	// Adding outputs from config
	for _, outputConfig := range config.Outputs {
		switch outputConfig["type"] {
		case "stdout":
			level := outputConfig["level"].(int)
			addOutput(&outputs.StdoutOutput{Level: level})
		case "fileout":
			level := outputConfig["level"].(int)
			path := outputConfig["path"].(string)
			addOutput(&outputs.FileOutput{Level: level, Path: path})
		case "TGBot":
			API_KEY := outputConfig["API_KEY"].(string)
			chats, err := convertMap(outputConfig["chats"].(map[interface{}]interface{}))
			if err != nil {
				log.Fatalf("Error loading users: %v", err)
				continue
			}
			_, minlevel := minMapValue(chats)
			addOutput(&outputs.TGOutput{Level: minlevel, Chats: chats, API_KEY: API_KEY})
		case "Elastic":
			level := outputConfig["level"].(int)
			login := outputConfig["login"].(string)
			password := outputConfig["password"].(string)
			host := outputConfig["host"].(string)
			index := outputConfig["index"].(string)
			addOutput(&outputs.ElasticOutput{Level: level, Login: login, Password: password, Host: host, Index: index})
		}
	}

	var worker_wg sync.WaitGroup

	// Start worker goroutines to process requests from the channel
	for i := 0; i < 5; i++ { // Start 5 workers
		worker_wg.Add(1)
		go func(id int) {
			defer worker_wg.Done()
			for reqData := range LogQueue {
				// Process the data
				processLog(reqData)
			}
			log.Printf("Worker %d exiting", id)
		}(i)
	}

	go func() {
		http.HandleFunc(config.WebSocketPath, handleWebSocket)
		log.Printf("Server started at :%s\n", config.Port)
		if err := http.ListenAndServe(fmt.Sprintf(":%s", config.Port), nil); err != nil {
			log.Fatal("ListenAndServe: ", err)
		}
	}()
	worker_wg.Wait()
	close(LogQueue)

}
