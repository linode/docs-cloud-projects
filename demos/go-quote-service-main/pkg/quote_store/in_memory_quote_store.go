package quote_store

import (
	om "github.com/the-gigi/go-quote-service/pkg/object_model"
)

type inMemoryQuoteStore struct {
	quotes []string
}

func (s *inMemoryQuoteStore) GetQuotes() ([]string, error) {
	return s.quotes, nil
}

func (s *inMemoryQuoteStore) AddQuote(quote string) error {
	s.quotes = append(s.quotes, quote)
	return nil
}

func NewInMemoryQuoteStore() (store om.QuoteStore) {
	return &inMemoryQuoteStore{}
}
