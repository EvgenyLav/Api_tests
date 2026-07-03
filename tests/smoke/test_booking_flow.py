import allure
import pytest

from models.booking_flow import (
    BookingResponse,
    GetTariffsResponse,
    RemovePlaceResponse,
    SelectPlaceResponse,
)
from models.routes_search import RoutesSearchResponse
from tests.builders.booking import build_booking_payload
from tests.helpers import (
    assert_ok_json,
    attach_json,
    attach_response,
    attach_text,
    get_route_details,
    pick_tariff_id,
    process_payment,
    search_route_for_carrier,
    select_place_ok,
)
from utils.constants import CARRIER_CONFIGS, LANG_RUS, EXPECTED_TARIFF_NAMES, EXPECTED_CURRENCIES


@allure.feature("Booking API")
@allure.story("Booking ticket smoke flow")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
def test_booking_ticket_flow(
    carrier_booking_context,
    routes_client,
    tickets_client,
    alphabank_client,
    place_cleanup,
):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    _, route_id, search_id = search_route_for_carrier(routes_client, carrier, valid_booking_depart_date)

    with allure.step("Get Search"):
        get_search_payload = {"SearchId": str(search_id), "Lang": LANG_RUS}
        attach_json(get_search_payload, "get_search_payload")
        get_search_response = routes_client.get_search(get_search_payload)
        attach_response(get_search_response, "get_search_response")

        assert_ok_json(get_search_response, "routes/getSearch")

        get_search_data = RoutesSearchResponse(**get_search_response.json())
        assert get_search_data.Result.CityDeparture == carrier["departure"]
        assert get_search_data.Result.CityArrival == carrier["arrival"]
        assert get_search_data.Result.all_routes

        route_group_check = get_search_data.Result.route_group_by_carrier(carrier["carrier_id"])
        assert route_group_check is not None
        assert route_group_check.Id == route_id

    route_details = get_route_details(routes_client, route_id, search_id, valid_booking_depart_date)
    if not route_details.has_seat_map:
        pytest.skip(f"У перевозчика '{carrier['name']}' свободная рассадка — выбор места не применим")
    assert route_details.free_bus_places, "Свободные места не найдены"

    first_place = route_details.free_bus_places[0]
    tariff_id = pick_tariff_id(route_details)
    attach_text(first_place, "first_place")
    if tariff_id is not None:
        attach_text(tariff_id, "tariff_id")

    with allure.step("Get Tariffs"):
        get_tariffs_payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        attach_json(get_tariffs_payload, "get_tariffs_payload")
        get_tariffs_response = routes_client.get_tariffs(get_tariffs_payload)
        attach_response(get_tariffs_response, "get_tariffs_response")

        assert_ok_json(get_tariffs_response, "routes/getTariffs")

        tariffs_data = GetTariffsResponse(**get_tariffs_response.json())
        assert tariffs_data.Result, "Тарифы не найдены"
        assert all(tariff.Name for tariff in tariffs_data.Result), "Есть тарифы без имени"

        returned_names = {tariff.Name for tariff in tariffs_data.Result}
        assert returned_names <= set(EXPECTED_TARIFF_NAMES), (
            f"Неожиданные тарифы: {returned_names - set(EXPECTED_TARIFF_NAMES)}"
        )

        for tariff in tariffs_data.Result:
            assert tariff.Prices, f"Цены не найдены для тарифа '{tariff.Name}'"
            for price in tariff.Prices:
                assert price.CurrencyName in EXPECTED_CURRENCIES, (
                    f"Неожиданная валюта '{price.CurrencyName}' в тарифе '{tariff.Name}'"
                )

    select_place_payload = {
        "NumberPlace": first_place,
        "RouteId": str(route_id),
        "SearchId": str(search_id),
        "Lang": LANG_RUS,
    }
    select_place_ok(tickets_client, select_place_payload)
    place_cleanup.track(select_place_payload)

    with allure.step("Select Place negative"):
        negative_select_response = tickets_client.select_place(select_place_payload)
        attach_response(negative_select_response, "select_place_negative_response")

        assert negative_select_response.status_code == 400
        assert negative_select_response.headers["Content-Type"].startswith("application/json")

        negative_select_data = SelectPlaceResponse(**negative_select_response.json())
        assert negative_select_data.Result.Success is False
        assert negative_select_data.Error is not None
        assert negative_select_data.Error.Message and "места заняты" in negative_select_data.Error.Message, (
            f"Ожидалась ошибка о занятых местах, получено: '{negative_select_data.Error.Message}'"
        )

    with allure.step("Remove Place"):
        remove_place_response = tickets_client.remove_place(select_place_payload)
        attach_response(remove_place_response, "remove_place_response")

        assert_ok_json(remove_place_response, "tickets/removeplace")

        remove_place_data = RemovePlaceResponse(**remove_place_response.json())
        assert remove_place_data.Result is True
        assert remove_place_data.Error is None
        place_cleanup.untrack(select_place_payload)

    select_place_ok(tickets_client, select_place_payload, step_name="Re-select Place")
    place_cleanup.track(select_place_payload)

    with allure.step("Booking Ticket"):
        booking_payload = build_booking_payload(
            route_id=route_id,
            search_id=search_id,
            place_number=first_place,
            tariff_id=tariff_id,
        )
        attach_json(booking_payload, "booking_payload")
        booking_response = tickets_client.booking(booking_payload)
        attach_response(booking_response, "booking_response")

        assert_ok_json(booking_response, "tickets/booking")

        booking_data = BookingResponse(**booking_response.json())
        assert booking_data.Error is None
        assert booking_data.Result is not None
        assert booking_data.Result.PaymentUrl
        md_order = booking_data.Result.md_order
        assert md_order is not None
        attach_text(md_order, "md_order")

        assert booking_data.Result.result is not None
        assert booking_data.Result.result.Data is not None
        assert booking_data.Result.result.Data.OrderId is not None
        assert booking_data.Result.result.Data.TicketsNumber is not None
        attach_text(booking_data.Result.result.Data.TicketsNumber, "ticket_number")
        place_cleanup.places_booked()

    process_payment(alphabank_client, md_order)
