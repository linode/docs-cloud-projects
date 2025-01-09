package object_model

type QuoteStore interface {
	GetQuotes() (quotes []string, err error)
	AddQuote(quote string) (err error)
}

type QuoteService interface {
	Run(port int)
}
