import random
import uuid

from utils.constants import LANG_RUS


def _random_suffix() -> str:
    return uuid.uuid4().hex[:8]


def build_booking_payload(route_id: int | str, search_id: int | str, place_number: int, tariff_id: int | None) -> dict:
    suffix = _random_suffix()
    passenger_tariff_id = tariff_id if tariff_id is not None else 3

    return {
        "Passengers": [
            {
                "FirstName": f"Test{suffix}",
                "LastName": f"User{suffix}",
                "MiddleName": "Petrovich",
                "Citizenship": "BY",
                "Birthdate": "1993-11-21",
                "Gender": "M",
                "DocumentId": "1",
                "DocumentNumber": f"12{random.randint(100000000, 999999999)}",
                "HasBonus": False,
                "TarifId": passenger_tariff_id,
                "PlaceNumber": place_number,
            }
        ],
        "Phone": f"+37529{random.randint(1000000, 9999999)}",
        "PhoneTwo": f"+37533{random.randint(1000000, 9999999)}",
        "Email": f"qa_{suffix}@example.com",
        "CurrencyId": 4,
        "PaySystem": "alphabank",
        "ExtraBaggage": 0,
        "PromoCode": "",
        "Note": f"autotest-{suffix}",
        "SiteVersionId": 2,
        "HasSubscription": False,
        "UserId": None,
        "RouteId": str(route_id),
        "SearchId": str(search_id),
        "Lang": LANG_RUS,
    }
