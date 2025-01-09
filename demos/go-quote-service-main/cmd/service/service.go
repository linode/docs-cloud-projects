package service

import (
	"encoding/json"
	"errors"
	"github.com/gorilla/mux"
	om "github.com/the-gigi/go-quote-service/pkg/object_model"
	"github.com/the-gigi/go-quote-service/pkg/quote_store"
	"net/http"
	"strconv"
)

type Service struct {
	router     *mux.Router
	quoteStore om.QuoteStore
}

type QuoteRequest struct {
	Quote string `json:"quote"` // Map the JSON field to the struct field
}

func (s *Service) register() {
	s.router.HandleFunc("/quotes", s.HandleNewQuote).Methods("POST")
	s.router.HandleFunc("/quotes", s.HandleGetQuotes)
}

func (s *Service) HandleGetQuotes(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	quotes, err := s.quoteStore.GetQuotes()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	err = json.NewEncoder(w).Encode(quotes)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	return
}

func (s *Service) HandleNewQuote(w http.ResponseWriter, r *http.Request) {
	if r.Body == nil {
		http.Error(w, "request body can't be nil", http.StatusBadRequest)
		return
	}

	var req QuoteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON format", http.StatusBadRequest)
		return
	}

	if err := s.quoteStore.AddQuote(req.Quote); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}

	return
}

func (s *Service) run(port int) (err error) {
	address := ":" + strconv.Itoa(port)
	err = http.ListenAndServe(address, s.router)
	if errors.Is(err, http.ErrServerClosed) {
		err = nil
	}
	return
}

func Run(port int, connectionString string) (err error) {
	s := Service{
		router: mux.NewRouter(),
	}

	if connectionString == "" {
		s.quoteStore = quote_store.NewInMemoryQuoteStore()
	} else {
		s.quoteStore, err = quote_store.NewPostgresQuoteStore(connectionString)
		if err != nil {
			return
		}
	}

	s.register()
	err = s.run(port)
	return
}
