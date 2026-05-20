MINSK = 1
MOSCOW = 3
LANG_RUS = "RUS"

EXPECTED_TARIFF_NAMES = [
    "DT (до 12 лет)",
    "ET (13...26 лет)",
    "PT (27...59 лет)",
    "ET (более 60 лет или инвалиды 1й - 2й групп)",
]

EXPECTED_CURRENCIES = ["BYN", "EUR", "RUB"]

CARRIER_CONFIGS = [
    {"name": "intercars", "departure": MINSK, "arrival": MOSCOW, "carrier_id": 1},
]
