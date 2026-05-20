# API Test Suite — Bus Ticket Booking

Automated API tests for a bus ticket booking service. The suite covers a full end-to-end booking flow across multiple carrier aggregators, with structured request/response validation via Pydantic models and Allure reporting.

## Tech Stack

- **Python 3.14** + **pytest** — test framework
- **Pydantic v2** — response schema validation
- **Allure** — test reporting
- **Docker** — containerised test runs
- **GitHub Actions** — CI/CD

## What Is Tested

### Smoke: full booking flow (`tests/smoke/test_booking_flow.py`)

Parametrised per carrier aggregator. Each run covers:

1. `POST /routes/search` — find available routes, verify departure/arrival cities and dates
2. `POST /routes/getSearch` — retrieve search session, assert route consistency
3. `POST /routes/getRoute` — get route details, verify seat availability and tariffs
4. `POST /routes/getTariffs` — validate tariff list and pricing structure
5. `POST /tickets/selectplace` — reserve a seat
6. `POST /tickets/selectplace` *(negative)* — attempt to reserve the same seat, expect `400` and error message
7. `POST /tickets/removeplace` — release the reserved seat
8. `POST /tickets/booking` — complete the booking, verify payment URL and order ID
9. `POST /alphabank/getStatus` — confirm order is registered but not yet paid

### Smoke: route search (`tests/smoke/test_routes_search.py`)

Standalone check of `POST /routes/search`: status, content type, city fields, route list, search ID.

## Project Structure

```
├── api/                  # HTTP clients (one class per API domain)
│   ├── base.py
│   ├── routes.py
│   ├── tickets.py
│   └── alphabank.py
├── config/
│   └── settings.py       # Env-based configuration
├── models/               # Pydantic response models
│   ├── booking_flow.py
│   └── routes_search.py
├── tests/
│   ├── builders/         # Payload factory functions
│   ├── smoke/            # Test files
│   └── conftest.py       # Fixtures and carrier configs
├── utils/
│   └── constants.py      # City IDs, carrier configs, expected values
├── .env.example
├── Dockerfile
└── .github/workflows/api-tests.yml
```

## Adding a New Carrier

Open `utils/constants.py` and add one entry to `CARRIER_CONFIGS`:

```python
CARRIER_CONFIGS = [
    {"name": "intercars", "departure": MINSK, "arrival": MOSCOW, "carrier_id": 1},
    {"name": "newcarrier", "departure": MOSCOW, "arrival": MINSK, "carrier_id": 42},
]
```

The booking flow test will automatically pick it up and run a separate parametrised case.

## Local Setup

```bash
cp .env.example .env
# fill in BASE_URL in .env

python -m pip install -r requirements.txt
pytest -m smoke --alluredir=allure-results --clean-alluredir
```

Open the report:

```bash
allure serve allure-results
```

## Docker

```bash
docker build -t api-tests .

docker run --rm \
  -e BASE_URL=http://your-api-base-url/api/v1 \
  -v "$PWD/allure-results:/app/allure-results" \
  api-tests
```

## CI — GitHub Actions

The workflow (`.github/workflows/api-tests.yml`) triggers on push to `main`/`master`, on pull requests, and manually via `workflow_dispatch`.

Each run:
- builds a Docker image and runs smoke tests inside it
- uploads raw `allure-results` as an artifact
- generates and uploads a full `allure-report` HTML artifact

**Required secret:** add `BASE_URL` in *Settings → Secrets and variables → Actions*.

> `RUN_TICKET_CREATION_CHECKS` — optional flag (`true`/`false`). When `true`, enables the final create-ticket and is-created checks, which trigger real ticket creation. Disabled by default.
