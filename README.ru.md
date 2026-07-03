    # API-тесты — бронирование автобусных билетов

[English](README.md) | **Русский**

Автотесты API сервиса бронирования автобусных билетов. Набор покрывает сквозные флоу для нескольких перевозчиков-агрегаторов — анонимное и авторизованное бронирование, мок оплаты, детали билета, аннуляцию и смену даты поездки — с валидацией запросов/ответов через Pydantic-модели и отчётностью в Allure.

## Стек

- **Python 3.14** + **pytest** — тестовый фреймворк
- **Pydantic v2** — валидация схем ответов
- **Faker** — тестовые данные пассажиров
- **Allure** — отчёты
- **Docker** — запуск в контейнере
- **GitHub Actions** — CI/CD

## Что покрыто

### Анонимный букинг-флоу (`tests/smoke/test_booking_flow.py`)

Параметризован по перевозчикам. Каждый прогон проверяет:

1. `POST /routes/search` — поиск маршрутов, проверка городов и дат
2. `POST /routes/getSearch` — получение поисковой сессии, консистентность маршрутов
3. `POST /routes/getRoute` — детали маршрута, свободные места и тарифы
4. `POST /routes/getTariffs` — список тарифов и структура цен
5. `POST /tickets/selectplace` — выбор места
6. `POST /tickets/selectplace` *(негатив)* — повторный выбор того же места, ожидается `400`
7. `POST /tickets/removeplace` — снятие выбранного места
8. `POST /tickets/booking` — бронирование, проверка платёжной ссылки и номера заказа
9. `POST /alphabank/status` — заказ зарегистрирован, но не оплачен

Для перевозчиков со свободной рассадкой скипается (схемы мест нет — выбор места не применим).

### Авторизованное бронирование (`tests/smoke/test_user_booking_flow.py`)

Выполняется под Bearer-токеном после логина:

- **Один билет**: выбор места → `tickets/user/booking` → мок оплаты (`alphabank/status` → `create` → `iscreated`) → `tickets/exists` → список `tickets/get` → `tickets/details` со сверкой данных пассажира → `tickets/annulation`
- **Мультибилет**: два места и два пассажира в одном заказе, сверка деталей по каждому (по месту, при свободной рассадке — по фамилии), аннуляция обоих билетов
- **Создание заказа**: для перевозчиков, чьи билеты стенд не выпускает, — бронь до созданного заказа с `OrderId`/`mdOrder`, без оплаты (неоплаченные заказы истекают на стороне стенда)

### Смена даты поездки (`tests/smoke/test_ticket_change_date.py`)

Фикстура-прекондишен `user_booked_ticket` бронирует и оплачивает билет, далее:

1. `tickets/details` — проверка `HasAbilityChangeDate`, фиксация исходной даты
2. Поиск маршрута на другую дату, выбор места
3. `tickets/changedate` — получение `OrderId` с информацией о возврате/доплате
4. `tickets/changedate/submit` — подтверждение смены
5. `tickets/details` — дата поездки действительно изменилась

В teardown фикстура аннулирует билет (best effort).

### Негативы бронирования (`tests/smoke/test_booking_negative.py`)

- Бронирование без обязательных полей (`Passengers`, `Phone`, `Email`) → `400` с сообщением об ошибке
- Бронирование места, занятого другой поисковой сессией → `400`

### Поиск маршрутов и авторизация (`tests/smoke/test_routes_search.py`, `test_auth.py`)

Отдельные проверки `POST /routes/search` и ручки получения токена.

## Перевозчики

Настраиваются в `utils/constants.py` → `CARRIER_CONFIGS`:

| Перевозчик | CarrierId | Маршрут | Схема мест | Выпуск билетов на стенде |
|---|---|---|---|---|
| intercars | 1 | Минск → Москва | есть | да — полные оплатные флоу |
| unitiki | 5 | Москва → Санкт-Петербург | свободная рассадка | нет — только тест брони |
| dist | 22 | Клайпеда → Рига | свободная рассадка | нет — только тест брони |

Поля конфига:

- `document_id` — тип документа пассажира; у каждого агрегатора свой справочник (приходит в `Result.DocumentTypes` ответа `routes/getRoute`)
- `issues_tickets` — `False` помечает перевозчиков, чьи билеты тестовый стенд не может выпустить через мок alphabank; оплатные флоу (оплата, детали, аннуляция, смена даты) для них скипаются и заменяются тестом брони. Когда стенд починят — переключить на `True`, правки тестов не нужны.

ID городов ищутся через `POST /cities/find` с телом `{"Name": "...", "isExactly": false, "Lang": "RUS"}`.

## Локальный запуск

```bash
cp .env.example .env
# заполнить BASE_URL, USER_LOGIN и USER_PASSWORD в .env

python -m pip install -r requirements.txt
```

## Команды запуска

```bash
# весь смоук с записью результатов Allure
pytest -m smoke --alluredir=allure-results --clean-alluredir

# один файл
pytest tests/smoke/test_ticket_change_date.py

# один перевозчик во всех параметризованных тестах
pytest -m smoke -k intercars

# по маркеру: smoke / booking / routes / auth
pytest -m booking
```

Открыть отчёт Allure (нужен [Allure CLI](https://allurereport.org/docs/install/), например `npm install -g allure-commandline`):

```bash
allure serve allure-results
```

## Структура проекта

```
├── api/                  # HTTP-клиенты (класс на домен API)
│   ├── base.py
│   ├── auth.py
│   ├── routes.py
│   ├── tickets.py
│   └── alphabank.py
├── config/
│   └── settings.py       # Конфигурация из переменных окружения
├── models/               # Pydantic-модели ответов
│   ├── booking_flow.py
│   ├── routes_search.py
│   └── user_booking.py
├── tests/
│   ├── builders/         # Фабрики payload'ов
│   ├── smoke/            # Тесты
│   ├── conftest.py       # Фикстуры (авторизация, контекст перевозчика, cleanup'ы)
│   └── helpers.py        # Общие шаги и проверки
├── utils/
│   └── constants.py      # ID городов, конфиги перевозчиков, ожидаемые значения
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

Воркфлоу (`.github/workflows/api-tests.yml`) запускается на пуш в `main`/`master`, на pull request и вручную через `workflow_dispatch`.

Каждый прогон:
- собирает Docker-образ и гоняет смоук внутри него (входной параметр `pytest_args` позволяет переопределить дефолтные `-m smoke`)
- выкладывает сырые `allure-results` как артефакт
- генерирует и выкладывает готовый HTML-отчёт `allure-report`
- публикует отчёт на GitHub Pages (для пушей и ручных запусков)

**Обязательные секреты:** `BASE_URL`, `USER_LOGIN` и `USER_PASSWORD` в *Settings → Secrets and variables → Actions*.

> `RUN_TICKET_CREATION_CHECKS` — необязательный флаг (`true`/`false`). При `true` включает финальные проверки create-ticket и is-created, которые реально создают билет. По умолчанию выключен.
