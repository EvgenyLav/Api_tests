import allure
import pytest
import json

from models.booking_flow import GetRouteResponse, SelectPlaceResponse
from models.routes_search import RoutesSearchResponse
from models.user_booking import (
    UserBookingResponse,
    TicketsListResponse,
    TicketDetailsResponse,
)
from tests.builders.booking import build_booking_payload
from utils.constants import CARRIER_CONFIGS, LANG_RUS


@allure.feature("Booking API")
@allure.story("User booking smoke flow")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
def test_user_booking_flow(
    carrier_booking_context,
    token_data,
    routes_client,
    user_tickets_client,
):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    with allure.step("Auth token"):
        assert token_data.access_token, "access_token пустой"
        assert token_data.token_type == "bearer"
        assert token_data.expires_in is not None and token_data.expires_in > 0, "expires_in некорректный"
        allure.attach(token_data.token_type, name="token_type", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(token_data.expires_in), name="expires_in", attachment_type=allure.attachment_type.TEXT)

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

    with allure.step("Get Route"):
        get_route_payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
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
        tariff_id = next((t.Id for t in route_details.Tariffs if t.Id is not None), None)
        allure.attach(str(first_place), name="first_place", attachment_type=allure.attachment_type.TEXT)
        if tariff_id is not None:
            allure.attach(str(tariff_id), name="tariff_id", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Select Place"):
        select_place_payload = {
            "NumberPlace": first_place,
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        select_response = user_tickets_client.select_place(select_place_payload)
        allure.attach(
            select_response.text,
            name="select_place_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert select_response.status_code in range(200, 300)
        assert select_response.headers["Content-Type"].startswith("application/json")
        select_data = SelectPlaceResponse(**select_response.json())
        assert select_data.Result.Success is True

    with allure.step("User Booking"):
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
        booking_response = user_tickets_client.user_booking(booking_payload)
        allure.attach(
            booking_response.text,
            name="booking_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert booking_response.status_code in range(200, 300)
        assert booking_response.headers["Content-Type"].startswith("application/json")

        booking_data = UserBookingResponse(**booking_response.json())
        assert booking_data.Error is None
        assert booking_data.Result is not None
        assert booking_data.Result.result is not None
        assert booking_data.Result.result.Data is not None

        order_id = booking_data.Result.result.Data.OrderId
        ticket_numbers = booking_data.Result.result.Data.TicketsNumber
        assert order_id is not None
        assert ticket_numbers is not None

        ticket_number_list = ticket_numbers if isinstance(ticket_numbers, list) else [ticket_numbers]
        allure.attach(str(order_id), name="order_id", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(ticket_numbers), name="ticket_numbers", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Get Tickets"):
        get_tickets_payload = {
            "Page": 1,
            "PageSize": 10,
            "UserId": None,
            "Status": 0,
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(get_tickets_payload, ensure_ascii=False, indent=2),
            name="get_tickets_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_tickets_response = user_tickets_client.get_tickets(get_tickets_payload)
        allure.attach(
            get_tickets_response.text,
            name="get_tickets_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_tickets_response.status_code in range(200, 300)
        assert get_tickets_response.headers["Content-Type"].startswith("application/json")

        tickets_data = TicketsListResponse(**get_tickets_response.json())
        assert tickets_data.Error is None
        assert tickets_data.Result is not None
        assert tickets_data.Result.Collections, "Список билетов пустой"
        assert tickets_data.Result.Count is not None and tickets_data.Result.Count > 0
        assert tickets_data.Result.CurrentPage == 1
        assert tickets_data.Result.PageSize == 10

        for ticket in tickets_data.Result.Collections:
            assert ticket.TicketNumber is not None
            assert ticket.PdfUrl is not None, f"PdfUrl отсутствует у билета {ticket.TicketNumber}"
            assert ticket.Price is not None and ticket.Price >= 0
            assert ticket.Currency is not None

        ticket_ids_in_list = {t.TicketNumber for t in tickets_data.Result.Collections}
        for tn in ticket_number_list:
            assert tn in ticket_ids_in_list, f"Забронированный билет {tn} не найден в списке билетов пользователя"

        first_ticket = tickets_data.Result.Collections[0]
        allure.attach(
            str(first_ticket.TicketNumber),
            name="first_ticket_number",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            str(first_ticket.PdfUrl),
            name="first_ticket_pdf_url",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Get Ticket Details"):
        details_payload = {
            "Number": first_ticket.TicketNumber,
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(details_payload, ensure_ascii=False, indent=2),
            name="ticket_details_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        details_response = user_tickets_client.get_ticket_details(details_payload)
        allure.attach(
            details_response.text,
            name="ticket_details_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert details_response.status_code in range(200, 300)
        assert details_response.headers["Content-Type"].startswith("application/json")

        details_data = TicketDetailsResponse(**details_response.json())
        assert details_data.Error is None
        assert details_data.Result is not None

        d = details_data.Result
        assert d.TicketNumber == first_ticket.TicketNumber, "TicketNumber в деталях не совпадает с запрошенным"
        assert d.ClientName, "ClientName пустой"
        assert d.PhoneNumber, "PhoneNumber пустой"
        assert d.DateDepart, "DateDepart пустой"
        assert d.PriceTicket is not None and d.PriceTicket > 0
        assert d.CurrencyName, "CurrencyName пустой"
        assert d.PdfUrl, "PdfUrl пустой в деталях"
        assert d.RouteDepart is not None, "RouteDepart отсутствует"
        assert d.RouteDepart.DepartTime, "DepartTime пустой"
        assert d.RouteDepart.ArriveTime, "ArriveTime пустой"
        assert d.HasAbilityChangeDate is not None, "HasAbilityChangeDate отсутствует"
        assert d.HasAbilityAnnulationTicket is not None, "HasAbilityAnnulationTicket отсутствует"


@allure.feature("Booking API")
@allure.story("User multi-ticket booking smoke flow")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
def test_user_multi_ticket_booking_flow(
    carrier_booking_context,
    token_data,
    routes_client,
    user_tickets_client,
):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    with allure.step("Auth token"):
        assert token_data.access_token, "access_token пустой"
        assert token_data.token_type == "bearer"
        assert token_data.expires_in is not None and token_data.expires_in > 0

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

    with allure.step("Get Route"):
        get_route_payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
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
        assert route_details.departure_date == valid_booking_depart_date

        free_places = route_details.free_bus_places
        if len(free_places) < 2:
            pytest.skip("Недостаточно свободных мест для теста (нужно минимум 2)")

        place_1, place_2 = free_places[0], free_places[1]
        tariff_id = next((t.Id for t in route_details.Tariffs if t.Id is not None), None)
        allure.attach(f"{place_1}, {place_2}", name="selected_places", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Select Place 1"):
        select_payload_1 = {
            "NumberPlace": place_1,
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        select_response_1 = user_tickets_client.select_place(select_payload_1)
        allure.attach(
            select_response_1.text,
            name="select_place_1_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert select_response_1.status_code in range(200, 300)
        assert select_response_1.headers["Content-Type"].startswith("application/json")
        assert SelectPlaceResponse(**select_response_1.json()).Result.Success is True

    with allure.step("Select Place 2"):
        select_payload_2 = {
            "NumberPlace": place_2,
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        select_response_2 = user_tickets_client.select_place(select_payload_2)
        allure.attach(
            select_response_2.text,
            name="select_place_2_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert select_response_2.status_code in range(200, 300)
        assert select_response_2.headers["Content-Type"].startswith("application/json")
        assert SelectPlaceResponse(**select_response_2.json()).Result.Success is True

    with allure.step("User Booking (2 билета)"):
        booking_payload = build_booking_payload(
            route_id=route_id,
            search_id=search_id,
            place_number=[place_1, place_2],
            tariff_id=tariff_id,
        )
        allure.attach(
            json.dumps(booking_payload, ensure_ascii=False, indent=2),
            name="booking_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        booking_response = user_tickets_client.user_booking(booking_payload)
        allure.attach(
            booking_response.text,
            name="booking_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert booking_response.status_code in range(200, 300)
        assert booking_response.headers["Content-Type"].startswith("application/json")

        booking_data = UserBookingResponse(**booking_response.json())
        assert booking_data.Error is None
        assert booking_data.Result is not None
        assert booking_data.Result.result is not None
        assert booking_data.Result.result.Data is not None

        order_id = booking_data.Result.result.Data.OrderId
        ticket_numbers = booking_data.Result.result.Data.TicketsNumber
        assert order_id is not None
        assert isinstance(ticket_numbers, list), (
            f"TicketsNumber должен быть списком при бронировании нескольких мест, получен: {type(ticket_numbers)}"
        )
        assert len(ticket_numbers) == 2, f"Ожидалось 2 билета, получено {len(ticket_numbers)}"
        allure.attach(str(order_id), name="order_id", attachment_type=allure.attachment_type.TEXT)
        allure.attach(str(ticket_numbers), name="ticket_numbers", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Get Tickets"):
        get_tickets_payload = {
            "Page": 1,
            "PageSize": 10,
            "UserId": None,
            "Status": 0,
            "Lang": LANG_RUS,
        }
        allure.attach(
            json.dumps(get_tickets_payload, ensure_ascii=False, indent=2),
            name="get_tickets_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        get_tickets_response = user_tickets_client.get_tickets(get_tickets_payload)
        allure.attach(
            get_tickets_response.text,
            name="get_tickets_response",
            attachment_type=allure.attachment_type.JSON,
        )

        assert get_tickets_response.status_code in range(200, 300)
        assert get_tickets_response.headers["Content-Type"].startswith("application/json")

        tickets_data = TicketsListResponse(**get_tickets_response.json())
        assert tickets_data.Error is None
        assert tickets_data.Result is not None
        assert tickets_data.Result.Count is not None and tickets_data.Result.Count >= 2

        ticket_ids_in_list = {t.TicketNumber for t in tickets_data.Result.Collections}
        for tn in ticket_numbers:
            assert tn in ticket_ids_in_list, (
                f"Забронированный билет {tn} не найден в списке билетов пользователя"
            )

    with allure.step("Get Ticket Details (оба билета)"):
        for ticket_number in ticket_numbers:
            details_payload = {"Number": ticket_number, "Lang": LANG_RUS}
            allure.attach(
                json.dumps(details_payload, ensure_ascii=False, indent=2),
                name=f"ticket_details_payload_{ticket_number}",
                attachment_type=allure.attachment_type.JSON,
            )
            details_response = user_tickets_client.get_ticket_details(details_payload)
            allure.attach(
                details_response.text,
                name=f"ticket_details_response_{ticket_number}",
                attachment_type=allure.attachment_type.JSON,
            )

            assert details_response.status_code in range(200, 300)
            assert details_response.headers["Content-Type"].startswith("application/json")

            details_data = TicketDetailsResponse(**details_response.json())
            assert details_data.Error is None
            assert details_data.Result is not None

            d = details_data.Result
            assert d.TicketNumber == ticket_number, f"TicketNumber в деталях не совпадает с запрошенным: {ticket_number}"
            assert d.ClientName, f"ClientName пустой у билета {ticket_number}"
            assert d.PhoneNumber, f"PhoneNumber пустой у билета {ticket_number}"
            assert d.DateDepart, f"DateDepart пустой у билета {ticket_number}"
            assert d.PriceTicket is not None and d.PriceTicket > 0
            assert d.CurrencyName, f"CurrencyName пустой у билета {ticket_number}"
            assert d.PdfUrl, f"PdfUrl пустой у билета {ticket_number}"
            assert d.RouteDepart is not None, f"RouteDepart отсутствует у билета {ticket_number}"
            assert d.RouteDepart.DepartTime, f"DepartTime пустой у билета {ticket_number}"
            assert d.RouteDepart.ArriveTime, f"ArriveTime пустой у билета {ticket_number}"
            assert d.HasAbilityChangeDate is not None, f"HasAbilityChangeDate отсутствует у билета {ticket_number}"
            assert d.HasAbilityAnnulationTicket is not None, f"HasAbilityAnnulationTicket отсутствует у билета {ticket_number}"
