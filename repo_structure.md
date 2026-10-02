# Repository Structure
```
fashion_rec/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── search.py
│   │       ├── products.py
│   │       ├── catalogue.py
│   │       └── health.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── query_schema.py
│   │   ├── product_schema.py
│   │   ├── search_response_schema.py
│   │   └── catalogue_schema.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── data_loader.py
│   └── observability/
│       ├── __init__.py
│       ├── logging.py
│       └── metrics.py
├── scripts/
│   ├── __init__.py
│   └── load_data.py
├── tests/
│   ├── __init__.py
│   └── ingestion/
│       ├── __init__.py
│       └── test_data_loader.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```
