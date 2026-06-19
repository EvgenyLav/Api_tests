import allure
import json
import pytest

from models.booking_flow import BookingResponse
from models.routes_search import RoutesSearchResponse
from tests.builders.booking import build_booking_payload
from utils.constants import CARRIER_CONFIGS


@allure.feature("Booking API")
@allure.story("Booking negative - missing required fields")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
@pytest.mark.parametrize("missing_field", ["Passengers", "Phone", "Email"])
def test_booking_missing_required_field(
    carrier_booking_context,
    selected_place_context,
    tickets_client,
    missing_field,
):
    ctx = selected_place_context
    payload = build_booking_payload(
        route_id=ctx["route_id"],
        search_id=ctx["search_id"],
        place_number=ctx["place_number"],
        tariff_id=ctx["tariff_id"],
    )
    del payload[missing_field]

    with allure.step(f"Booking без поля '{missing_field}'"):
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2),
            name="payload",
            attachment_type=allure.attachment_type.JSON,
        )
        response = tickets_client.booking(payload)
        allure.attach(
            response.text,
            name="response",
            attachment_type=allure.attachment_type.JSON,
        )

    assert response.status_code == 400, (
        f"Ожидался 400 при отсутствии '{missing_field}', "
        f"получен {response.status_code}. Body: {response.text}"
    )
    assert response.headers["Content-Type"].startswith("application/json")
    data = response.json()
    assert data.get("Error") is not None, (
        f"Ожидалось поле Error в ответе при отсутствии '{missing_field}'. Body: {response.text}"
    )
    assert data["Error"].get("Message"), (
        f"Ожидалось непустое Error.Message при отсутствии '{missing_field}'. Body: {response.text}"
    )


@allure.feature("Booking API")
@allure.story("Booking negative - already occupied place")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
def test_booking_occupied_place(
    carrier_booking_context,
    selected_place_context,
    routes_client,
    tickets_client,
):
    ctx = selected_place_context
    carrier = ctx["carrier"]

    with allure.step("Новый поисковый сеанс для того же маршрута"):
        second_search_data = RoutesSearchResponse(
            **routes_client.search_routes({
                "CityDeparture": carrier["departure"],
                "CityArrival": carrier["arrival"],
                "DateDeparture": carrier["date"],
            }).json()
        )
        second_search_id = second_search_data.Result.Id
        allure.attach(
            str(second_search_id),
            name="second_search_id",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Попытка забронировать занятое место из другого сеанса"):
        payload = build_booking_payload(
            route_id=ctx["route_id"],
            search_id=second_search_id,
            place_number=ctx["place_number"],
            tariff_id=ctx["tariff_id"],
        )
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2),
            name="payload",
            attachment_type=allure.attachment_type.JSON,
        )
        response = tickets_client.booking(payload)
        allure.attach(
            response.text,
            name="response",
            attachment_type=allure.attachment_type.JSON,
        )

    assert response.status_code == 400, (
        f"Ожидался 400 для занятого места, получен {response.status_code}. Body: {response.text}"
    )
    assert response.headers["Content-Type"].startswith("application/json")
    data = BookingResponse(**response.json())
    assert data.Result is None or not data.Result.PaymentUrl, (
        f"Ожидался пустой Result для занятого места. Body: {response.text}"
    )
    assert data.Error is not None, (
        f"Ожидалось поле Error для занятого места. Body: {response.text}"
    )
