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
        allure.attach(token_data.token_type, name="token_type", attachment_type=allure.attachment_type.TEXT)

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
        search_data = RoutesSearchResponse(**search_response.json())
        route_group = search_data.Result.route_group_by_carrier(carrier["carrier_id"])
        assert route_group is not None, f"Маршруты агрегатора '{carrier['name']}' не найдены"

        route_id = route_group.Id
        search_id = search_data.Result.Id

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
        route_data = GetRouteResponse(**get_route_response.json())
        route_details = route_data.Result.Route

        assert route_details.free_bus_places, "Свободные места не найдены"
        first_place = route_details.free_bus_places[0]
        tariff_id = next((t.Id for t in route_details.Tariffs if t.Id is not None), None)

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
        assert tickets_data.Result.Count > 0

        for ticket in tickets_data.Result.Collections:
            assert ticket.TicketNumber is not None
            assert ticket.PdfUrl is not None, f"PdfUrl отсутствует у билета {ticket.TicketNumber}"
            assert ticket.Price is not None and ticket.Price >= 0
            assert ticket.Currency is not None

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
