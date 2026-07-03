MINSK = 1
SAINT_PETERSBURG = 2
MOSCOW = 3
KLAIPEDA = 485
RIGA = 488
MINSK_NAME = "Минск"
MOSCOW_NAME = "Москва"
LANG_RUS = "RUS"

EXPECTED_TARIFF_NAMES = [
    "DT (до 12 лет)",
    "ET (13...26 лет)",
    "PT (27...59 лет)",
    "ET (более 60 лет или инвалиды 1й - 2й групп)",
    "Льготный 12",
    "Детский (до 12 лет) 12",
    "Детский (до 6 лет)",
    "Полный 12",
]

EXPECTED_CURRENCIES = ["BYN", "EUR", "RUB"]

# document_id — тип документа из Result.DocumentTypes ответа getRoute:
# справочник у каждого агрегатора свой, комбинация должна соответствовать Citizenship=BY
# issues_tickets=False — тестовый стенд не выпускает билеты агрегатора через мок
# alphabank (create зависает «in process»/NullReference), поэтому оплатные флоу скипаются
CARRIER_CONFIGS = [
    {
        "name": "intercars",
        "departure": MINSK,
        "arrival": MOSCOW,
        "carrier_id": 1,
        "document_id": "1",
        "issues_tickets": True,
    },
    {
        "name": "unitiki",
        "departure": MOSCOW,
        "arrival": SAINT_PETERSBURG,
        "carrier_id": 5,
        "document_id": "52",
        "issues_tickets": False,
    },
    {
        "name": "dist",
        "departure": KLAIPEDA,
        "arrival": RIGA,
        "carrier_id": 22,
        "document_id": "passport_id",
        "issues_tickets": False,
    },
]
