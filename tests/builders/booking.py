from faker import Faker

from utils.constants import LANG_RUS

fake = Faker("ru_RU")


def build_booking_payload(route_id: int | str, search_id: int | str, place_number: int, tariff_id: int | None) -> dict:
    passenger_tariff_id = tariff_id if tariff_id is not None else 3

    return {
        "Passengers": [
            {
                "FirstName": fake.first_name_male(),
                "LastName": fake.last_name_male(),
                "MiddleName": fake.middle_name_male(),
                "Citizenship": "BY",
                "Birthdate": fake.date_of_birth(minimum_age=18, maximum_age=70).strftime("%Y-%m-%d"),
                "Gender": "M",
                "DocumentId": "1",
                "DocumentNumber": f"12{fake.numerify('#########')}",
                "HasBonus": False,
                "TarifId": passenger_tariff_id,
                "PlaceNumber": place_number,
            }
        ],
        "Phone": fake.numerify("+37529#######"),
        "PhoneTwo": fake.numerify("+37533#######"),
        "Email": fake.ascii_free_email(),
        "CurrencyId": 4,
        "PaySystem": "alphabank",
        "ExtraBaggage": 0,
        "PromoCode": "",
        "Note": f"autotest-{fake.uuid4()[:8]}",
        "SiteVersionId": 2,
        "HasSubscription": False,
        "UserId": None,
        "RouteId": str(route_id),
        "SearchId": str(search_id),
        "Lang": LANG_RUS,
    }
