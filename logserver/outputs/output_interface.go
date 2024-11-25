package outputs

type Log struct {
	Level int    `json:"level"`
	Msg   string `json:"msg"`
	IP    string `json:"ip"`
	Login string `json:"login"`
}

type Output interface {
	Process(log Log) error
	GetLevel() int
}
