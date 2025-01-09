package main

import (
	"fmt"
	"github.com/the-gigi/go-quote-service/cmd/service"
	"os"
)

func main() {
	var port = 7777

	connectionString := os.Getenv("GO_QUOTE_SERVICE_CONNECTION_STRING")
	fmt.Println("Listening on port ", port)
	err := service.Run(port, connectionString)
	if err != nil {
		fmt.Printf("%v\n", err)
		os.Exit(1)
	}
}
