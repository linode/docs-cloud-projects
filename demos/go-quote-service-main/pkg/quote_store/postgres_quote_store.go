package quote_store

import (
	"database/sql"
	"fmt"
	_ "github.com/lib/pq"
	"github.com/the-gigi/go-quote-service/pkg/db_util"
	om "github.com/the-gigi/go-quote-service/pkg/object_model"
)

type postgresQuoteStore struct {
	db *sql.DB
}

// createSchema creates the quotes table if it doesn't exist already
func (p *postgresQuoteStore) createSchema() (err error) {
	schema := `CREATE TABLE IF NOT EXISTS quotes (
          id SERIAL PRIMARY KEY,
          quote TEXT UNIQUE
        );
    `
	_, err = p.db.Exec(schema)
	return
}

func (p *postgresQuoteStore) GetQuotes() (quotes []string, err error) {
	q := "SELECT quote FROM quotes"
	rows, err := p.db.Query(q)
	if err != nil {
		return
	}

	var quote string
	for rows.Next() {
		err = rows.Scan(&quote)
		if err != nil {
			return
		}

		quotes = append(quotes, quote)
	}
	return
}

func (p *postgresQuoteStore) AddQuote(quote string) (err error) {
	t := "INSERT INTO quotes (quote) VALUES ('%s')"
	command := fmt.Sprintf(t, quote)
	_, err = p.db.Exec(command)
	return
}

func connect(connectionString string) (db *sql.DB, err error) {
	db, err = sql.Open("postgres", connectionString)
	if err != nil {
		return
	}

	err = db.Ping()
	if err != nil {
		return
	}

	return
}

func NewPostgresQuoteStore(connectionString string) (store om.QuoteStore, err error) {
	var db *sql.DB
	if connectionString == "" {
		db, err = db_util.RunLocalDB("quotes")
	} else {
		db, err = connect(connectionString)
	}
	if err != nil {
		return
	}
	p := &postgresQuoteStore{
		db: db,
	}

	err = p.createSchema()
	if err != nil {
		return
	}

	store = p
	return
}
