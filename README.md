# API Test Suite — Bus Ticket Booking

**English** | [Русский](README.ru.md)

Automated API tests for a bus ticket booking service. The suite covers end-to-end booking flows across multiple carrier aggregators — anonymous and authorized booking, payment mock, ticket details, annulment and departure date change — with structured request/response validation via Pydantic models and Allure reporting.

## Tech Stack

- **Python 3.14** + **pytest** — test framework
- **Pydantic v2** — response schema validation
- **Faker** — passenger test data
- **Allure** — test reporting
- **Docker** — containerised test runs
- **GitHub Actions** — CI/CD

## What Is Tested

### Anonymous booking flow (`tests/smoke/test_booking_flow.py`)

Parametrised per carrier aggregator. Each run covers:

1. `POST /routes/search` — find available routes, verify departure/arrival cities and dates
2. `POST /routes/getSearch` — retrieve search session, assert route consistency
3. `POST /routes/getRoute` — get route details, verify seat availability and tariffs
4. `POST /routes/getTariffs` — validate tariff list and pricing structure
5. `POST /tickets/selectplace` — reserve a seat
6. `POST /tickets/selectplace` *(negative)* — attempt to reserve the same seat, expect `400`
7. `POST /tickets/removeplace` — release the reserved seat
8. `POST /tickets/booking` — complete the booking, verify payment URL and order ID
9. `POST /alphabank/status` — confirm order is registered but not yet paid

Skipped for free-seating carriers (no seat map — seat selection is not applicable).

### Authorized user booking (`tests/smoke/test_user_booking_flow.py`)

Runs under a Bearer token obtained via login:

- **Single ticket**: select place → `tickets/user/booking` → payment mock (`alphabank/status` → `create` → `iscreated`) → `tickets/exists` → `tickets/get` list → `tickets/details` matched against passenger data → `tickets/annulation`
- **Multi-ticket**: two seats and two passengers in one order, details matched per passenger (by seat, or by name for free seating), both tickets annulled
- **Order created**: for carriers whose tickets the test stand cannot issue — booking up to a created order with `OrderId`/`mdOrder`, no payment (unpaid orders expire server-side)

### Departure date change (`tests/smoke/test_ticket_change_date.py`)

Precondition fixture `user_booked_ticket` books and pays for a ticket, then:

1. `tickets/details` — verify `HasAbilityChangeDate`, capture the original date
2. Search a route on a different date, select a seat
3. `tickets/changedate` — get `OrderId` with refund/extra-pay info
4. `tickets/changedate/submit` — confirm the change
5. `tickets/details` — verify the departure date actually changed

The fixture annuls the ticket in teardown (best effort).

### Booking negatives (`tests/smoke/test_booking_negative.py`)

- Booking without required fields (`Passengers`, `Phone`, `Email`) → `400` with an error message
- Booking a seat already held by another search session → `400`

### Route search and auth (`tests/smoke/test_routes_search.py`, `test_auth.py`)

Standalone checks of `POST /routes/search` and the token endpoint.

## Carriers

Configured in `utils/constants.py` → `CARRIER_CONFIGS`:

| Carrier | CarrierId | Route | Seat map | Ticket issuance on stand |
|---|---|---|---|---|
| intercars | 1 | Minsk → Moscow | yes | yes — full paid flows |
| unitiki | 5 | Moscow → St. Petersburg | free seating | no — booking-only test |
| dist | 22 | Klaipeda → Riga | free seating | no — booking-only test |

Config fields:

- `document_id` — passenger document type; each aggregator has its own reference list (returned in `Result.DocumentTypes` of `routes/getRoute`)
- `issues_tickets` — `False` marks carriers whose tickets the test stand cannot issue through the alphabank mock; paid flows (payment, details, annulment, date change) are skipped for them and covered by the booking-only test instead. Flip to `True` once the stand is fixed — no test changes needed.

City IDs can be resolved via `POST /cities/find` with `{"Name": "...", "isExactly": false, "Lang": "RUS"}`.

## Local Setup

```bash
cp .env.example .env
# fill in BASE_URL, USER_LOGIN and USER_PASSWORD in .env

python -m pip install -r requirements.txt
```

## Running Tests

```bash
# full smoke suite with Allure results
pytest -m smoke --alluredir=allure-results --clean-alluredir

# a single test file
pytest tests/smoke/test_ticket_change_date.py

# a single carrier across all parametrised tests
pytest -m smoke -k intercars

# by marker: smoke / booking / routes / auth
pytest -m booking
```

Open the Allure report (requires the [Allure CLI](https://allurereport.org/docs/install/), e.g. `npm install -g allure-commandline`):

```bash
allure serve allure-results
```

## Project Structure

```
├── api/                  # HTTP clients (one class per API domain)
│   ├── base.py
│   ├── auth.py
│   ├── routes.py
│   ├── tickets.py
│   └── alphabank.py
├── config/
│   └── settings.py       # Env-based configuration
├── models/               # Pydantic response models
│   ├── booking_flow.py
│   ├── routes_search.py
│   └── user_booking.py
├── tests/
│   ├── builders/         # Payload factory functions
│   ├── smoke/            # Test files
│   ├── conftest.py       # Fixtures (auth, carrier context, cleanups)
│   └── helpers.py        # Shared test steps and assertions
├── utils/
│   └── constants.py      # City IDs, carrier configs, expected values
├── .env.example
├── Dockerfile
└── .github/workflows/api-tests.yml
```

## Docker

```bash
docker build -t api-tests .

docker run --rm \
  -e BASE_URL=http://your-api-base-url/api/v1 \
  -e USER_LOGIN=your_phone \
  -e USER_PASSWORD=your_password \
  -v "$PWD/allure-results:/app/allure-results" \
  api-tests
```

## CI — GitHub Actions

The workflow (`.github/workflows/api-tests.yml`) triggers on push to `main`/`master`, on pull requests, and manually via `workflow_dispatch`.

Each run:
- builds a Docker image and runs smoke tests inside it (`pytest_args` input lets you override the default `-m smoke`)
- uploads raw `allure-results` as an artifact
- generates and uploads a full `allure-report` HTML artifact
- deploys the report to GitHub Pages (on push and manual runs)

**Required secrets:** add `BASE_URL`, `USER_LOGIN` and `USER_PASSWORD` in *Settings → Secrets and variables → Actions*.

> `RUN_TICKET_CREATION_CHECKS` — optional flag (`true`/`false`). When `true`, enables the final create-ticket and is-created checks, which trigger real ticket creation. Disabled by default.
