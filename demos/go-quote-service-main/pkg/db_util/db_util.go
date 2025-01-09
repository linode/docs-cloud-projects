package db_util

import (
	"database/sql"
	"fmt"
	sq "github.com/Masterminds/squirrel"
	_ "github.com/lib/pq"
	"log"
	"os"
	"os/exec"
	"strconv"
	"strings"
)

type Params struct {
	Host     string
	Port     int
	User     string
	Password string
	DbName   string
	SslMode  string
}

func defaultParams() Params {
	return Params{
		Host:     "localhost",
		Port:     5432,
		User:     "postgres",
		Password: "postgres",
		SslMode:  "disable",
	}
}

func RunLocalDB(dbName string) (db *sql.DB, err error) {
	// Launch the DB if not running
	out, err := exec.Command("docker", "ps", "-f", "name=postgres", "--format", "{{.Names}}").CombinedOutput()
	if err != nil {
		return
	}

	s := string(out)
	if s == "" {
		out, err = exec.Command("docker", "restart", "postgres").CombinedOutput()
		if err != nil {
			log.Print(string(out))
			_, err = exec.Command("docker", "run", "-d", "--name", "postgres",
				"-p", "5432:5432",
				"-e", "POSTGRES_PASSWORD=postgres",
				"postgres:alpine").CombinedOutput()

		}
		if err != nil {
			return
		}
	}

	p := defaultParams()
	db, err = EnsureDB(p)
	return
}

func connectToDB(p Params) (db *sql.DB, err error) {
	mask := "host=%s port=%d user=%s password=%s dbname=%s sslmode=%s"
	dcn := fmt.Sprintf(mask, p.Host, p.Port, p.User, p.Password, p.DbName, p.SslMode)
	db, err = sql.Open("postgres", dcn)
	return
}

// EnsureDB ensures sure the database exists (creates it if it doesn't)
func EnsureDB(p Params) (db *sql.DB, err error) {
	dbName := p.DbName
	// Connect to the postgres DB
	p.DbName = "postgres"
	postgresDb, err := connectToDB(p)
	if err != nil {
		return
	}

	// Check if the DB exists in the list of databases
	var count int
	sb := sq.StatementBuilder.PlaceholderFormat(sq.Dollar)
	q := sb.Select("count(*)").From("pg_database").Where(sq.Eq{"datname": dbName})
	err = q.RunWith(postgresDb).QueryRow().Scan(&count)
	if err != nil {
		return
	}

	// If it doesn't exist create it
	if count == 0 {
		_, err = postgresDb.Exec("CREATE database " + dbName)
		if err != nil {
			return
		}
	}

	// Connect to the DB
	p.DbName = dbName
	db, err = connectToDB(p)
	return
}

func DeleteFromTableIfExist(db *sql.DB, table string) error {
	_, err := db.Exec("DELETE from " + table)
	if err != nil {
		expected := fmt.Sprintf("pq: relation \"%s\" does not exist", table)
		message := err.Error()
		if message != expected {
			return err
		}
	}
	return nil
}

func GetDbEndpoint(serviceName string) (host string, port int, err error) {
	hostEnvVar := strings.ToUpper(serviceName) + "_DB_SERVICE_HOST"
	host = os.Getenv(hostEnvVar)
	if host == "" {
		host = "localhost"
	}

	portEnvVar := strings.ToUpper(serviceName) + "_DB_SERVICE_PORT"
	dbPort := os.Getenv(portEnvVar)
	if dbPort == "" {
		dbPort = "5432"
	}

	port, err = strconv.Atoi(dbPort)
	log.Println("DB host:", host, "DB port:", dbPort)
	return
}
