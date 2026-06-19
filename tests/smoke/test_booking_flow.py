import allure
import pytest
import json

from models.booking_flow import (
    BookingResponse,
    CreateTicketResponse,
    GetRouteResponse,
    GetTariffsResponse,
    IsCreatedResponse,
    PaymentStatusResponse,
    RemovePlaceResponse,
    SelectPlaceResponse,
)
from tests.builders.alphabank import build_status_payload, build_validation_payload
from models.routes_search import RoutesSearchResponse
from tests.builders.booking import build_booking_payload
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
def test_booking_ticket_flow(carrier_booking_context, routes_client, tickets_client, alphabank_client):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    with allure.step("Search Routes"):
        search_payload = {
            "CityDeparture": carrier["departure"],
            "CityArrival": carrier["arrival"],
            "DateDeparture": valid_booking_depart_date,
        }
        allure.attach(
            json.dumps(search_payload, ensure_ascii=False, indent=2),
            name="search_routes_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        search_response = routes_client.search_routes(search_payload)
        allure.attach(
            search_response.text,
            name="search_routes_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert search_response.status_code in range(200, 300)
        assert search_response.headers["Content-Type"].startswith("application/json")

        search_data = RoutesSearchResponse(**search_response.json())
        assert search_data.Result.CityDeparture == carrier["departure"]
        assert search_data.Result.CityArrival == carrier["arrival"]
        assert search_data.Result.Id is not None
        assert search_data.Result.all_routes, "Маршруты не найдены"

        route_group = search_data.Result.route_group_by_carrier(carrier["carrier_id"])
        assert route_group is not None, f"Маршруты агрегатора '{carrier['name']}' не найдены"
        assert route_group.departure_date == valid_booking_depart_date

        route_id = route_group.Id
        search_id = search_data.Result.Id
        assert route_id is not None, "Id маршрута не найден в ответе routes/search"
        allure.attach(str(search_id), name="search_id", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(route_id), name="route_id", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Get Search"):
        get_search_payload = {"SearchId": str(search_id), "Lang": LANG_RUS}
        allure.attach(
            json.dumps(get_search_payload, ensure_ascii=False, indent=2),
            name="get_search_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_search_response = routes_client.get_search(get_search_payload)
        allure.attach(
            get_search_response.text,
            name="get_search_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_search_response.status_code in range(200, 300)
        assert get_search_response.headers["Content-Type"].startswith("application/json")

        get_search_data = RoutesSearchResponse(**get_search_response.json())
        assert get_search_data.Result.CityDeparture == carrier["departure"]
        assert get_search_data.Result.CityArrival == carrier["arrival"]
        assert get_search_data.Result.all_routes

        route_group_check = get_search_data.Result.route_group_by_carrier(carrier["carrier_id"])
        assert route_group_check is not None
        assert route_group_check.Id == route_id

    with allure.step("Get Route"):
        get_route_payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(get_route_payload, ensure_ascii=False, indent=2),
            name="get_route_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_route_response = routes_client.get_route(get_route_payload)
        allure.attach(
            get_route_response.text,
            name="get_route_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_route_response.status_code in range(200, 300)
        assert get_route_response.headers["Content-Type"].startswith("application/json")

        route_data = GetRouteResponse(**get_route_response.json())
        route_details = route_data.Result.Route

        assert str(route_details.Id) == str(route_id)
        assert route_details.City1 and route_details.City2
        assert route_details.Tariffs
        assert route_details.FullBusPlaces
        assert route_details.free_bus_places, "Свободные места не найдены"
        assert route_details.departure_date == valid_booking_depart_date

        first_place = route_details.free_bus_places[0]
        tariff_id = next((tariff.Id for tariff in route_details.Tariffs if tariff.Id is not None), None)
        allure.attach(str(first_place), name="first_place", attachment_type=allure.attachment_type.TEXT)
        if tariff_id is not None:
            allure.attach(str(tariff_id), name="tariff_id", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Get Tariffs"):
        get_tariffs_payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(get_tariffs_payload, ensure_ascii=False, indent=2),
            name="get_tariffs_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_tariffs_response = routes_client.get_tariffs(get_tariffs_payload)
        allure.attach(
            get_tariffs_response.text,
            name="get_tariffs_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_tariffs_response.status_code in range(200, 300)
        assert get_tariffs_response.headers["Content-Type"].startswith("application/json")

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

    with allure.step("Select Place"):
        select_place_payload = {
            "NumberPlace": first_place,
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(select_place_payload, ensure_ascii=False, indent=2),
            name="select_place_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        select_place_response = tickets_client.select_place(select_place_payload)
        allure.attach(
            select_place_response.text,
            name="select_place_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert select_place_response.status_code in range(200, 300)
        assert select_place_response.headers["Content-Type"].startswith("application/json")

        select_place_data = SelectPlaceResponse(**select_place_response.json())
        assert select_place_data.Result.Success is True

    with allure.step("Select Place negative"):
        negative_select_response = tickets_client.select_place(select_place_payload)
        allure.attach(
            negative_select_response.text,
            name="select_place_negative_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert negative_select_response.status_code == 400
        assert negative_select_response.headers["Content-Type"].startswith("application/json")

        negative_select_data = SelectPlaceResponse(**negative_select_response.json())
        assert negative_select_data.Result.Success is False
        assert negative_select_data.Error is not None
        assert (
            negative_select_data.Error.Message
            == "К сожалению выбранные места заняты, , попробуйте выбрать другое место"
        )

    with allure.step("Remove Place"):
        remove_place_response = tickets_client.remove_place(select_place_payload)
        allure.attach(
            remove_place_response.text,
            name="remove_place_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert remove_place_response.status_code in range(200, 300)
        assert remove_place_response.headers["Content-Type"].startswith("application/json")

        remove_place_data = RemovePlaceResponse(**remove_place_response.json())
        assert remove_place_data.Result is True
        assert remove_place_data.Error is None

    with allure.step("Re-select Place"):
        reselect_response = tickets_client.select_place(select_place_payload)
        allure.attach(
            reselect_response.text,
            name="reselect_place_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert reselect_response.status_code in range(200, 300)
        assert reselect_response.headers["Content-Type"].startswith("application/json")

        reselect_data = SelectPlaceResponse(**reselect_response.json())
        assert reselect_data.Result.Success is True

    with allure.step("Booking Ticket"):
        booking_payload = build_booking_payload(
            route_id=route_id,
            search_id=search_id,
            place_number=first_place,
            tariff_id=tariff_id,
        )
        allure.attach(
            json.dumps(booking_payload, ensure_ascii=False, indent=2),
            name="booking_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        booking_response = tickets_client.booking(booking_payload)
        allure.attach(
            booking_response.text,
            name="booking_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert booking_response.status_code in range(200, 300)
        assert booking_response.headers["Content-Type"].startswith("application/json")

        booking_data = BookingResponse(**booking_response.json())
        assert booking_data.Error is None
        assert booking_data.Result.PaymentUrl
        assert booking_data.Result.md_order is not None
        allure.attach(booking_data.Result.md_order, name="md_order", attachment_type=allure.attachment_type.TEXT)

        assert booking_data.Result.result is not None
        assert booking_data.Result.result.Data is not None
        assert booking_data.Result.result.Data.OrderId is not None
        assert booking_data.Result.result.Data.TicketsNumber is not None
        ticket_number = booking_data.Result.result.Data.TicketsNumber
        allure.attach(str(ticket_number), name="ticket_number", attachment_type=allure.attachment_type.TEXT)

    status_payload = build_status_payload(booking_data.Result.md_order)
    validation_payload = build_validation_payload(booking_data.Result.md_order)

    with allure.step("Get Status"):
        allure.attach(
            json.dumps(status_payload, ensure_ascii=False, indent=2),
            name="get_status_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_status_response = alphabank_client.get_status(status_payload)
        allure.attach(
            get_status_response.text,
            name="get_status_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_status_response.status_code in range(200, 300)
        assert get_status_response.headers["Content-Type"].startswith("application/json")

        status_data = PaymentStatusResponse(**get_status_response.json())
        assert status_data.Result.Success is False
        assert status_data.Result.Status == "0: Заказ зарегистрирован, но не оплачен"
        assert status_data.Error is None

    with allure.step("Create ticket"):
        allure.attach(
            json.dumps(validation_payload, ensure_ascii=False, indent=2),
            name="create_ticket_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        create_ticket_response = alphabank_client.create_ticket(validation_payload)
        allure.attach(
            create_ticket_response.text,
            name="create_ticket_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert create_ticket_response.status_code in range(200, 300)
        assert create_ticket_response.headers["Content-Type"].startswith("application/json")

        create_ticket_data = CreateTicketResponse(**create_ticket_response.json())
        assert create_ticket_data.Result.Success is True
        assert create_ticket_data.Result.Data is True
        assert create_ticket_data.Error is None

    with allure.step("Is Created"):
        allure.attach(
            json.dumps(validation_payload, ensure_ascii=False, indent=2),
            name="is_created_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        is_created_response = alphabank_client.is_created(validation_payload)
        allure.attach(
            is_created_response.text,
            name="is_created_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert is_created_response.status_code in range(200, 300)
        assert is_created_response.headers["Content-Type"].startswith("application/json")

        is_created_data = IsCreatedResponse(**is_created_response.json())
        assert is_created_data.Error is None
        assert is_created_data.Result is True, f"Билет не создан: Result={is_created_data.Result}"
