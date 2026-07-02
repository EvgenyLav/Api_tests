import allure
import pytest

from models.user_booking import (
    UserBookingResponse,
    TicketsListResponse,
    TicketDetailsResponse,
    TicketAnnulationResponse,
)
from tests.builders.booking import build_booking_payload
from tests.helpers import (
    assert_ok_json,
    assert_ticket_details_match,
    attach_json,
    attach_response,
    attach_text,
    get_route_details,
    pick_tariff_id,
    process_payment,
    search_route_for_carrier,
    select_place_ok,
)
from utils.constants import CARRIER_CONFIGS, LANG_RUS


def _do_user_booking(user_tickets_client, booking_payload: dict, step_name: str = "User Booking"):
    """Шаг User Booking: бронирует и возвращает (order_id, ticket_numbers, md_order)."""
    with allure.step(step_name):
        attach_json(booking_payload, "booking_payload")
        booking_response = user_tickets_client.user_booking(booking_payload)
        attach_response(booking_response, "booking_response")

        assert_ok_json(booking_response, "tickets/user/booking")

        booking_data = UserBookingResponse(**booking_response.json())
        assert booking_data.Error is None
        assert booking_data.Result is not None
        assert booking_data.Result.result is not None
        assert booking_data.Result.result.Data is not None

        order_id = booking_data.Result.result.Data.OrderId
        ticket_numbers = booking_data.Result.result.Data.TicketsNumber
        assert order_id is not None
        assert ticket_numbers is not None
        attach_text(order_id, "order_id")
        attach_text(ticket_numbers, "ticket_numbers")

        md_order = booking_data.Result.md_order
        assert md_order is not None, "mdOrder не найден в ответе user_booking"
        attach_text(md_order, "md_order")

    return order_id, ticket_numbers, md_order


def _assert_tickets_exist(user_tickets_client, ticket_numbers: list):
    with allure.step("Ticket Exists"):
        for tn in ticket_numbers:
            exists_payload = {"Number": tn, "Lang": LANG_RUS}
            exists_response = user_tickets_client.ticket_exists(exists_payload)
            attach_response(exists_response, f"ticket_exists_response_{tn}")

            assert_ok_json(exists_response, f"tickets/exists (билет {tn})")
            assert exists_response.json() is True, f"Билет {tn} не найден в системе"


def _get_ticket_details(user_tickets_client, ticket_number: str):
    """Запрашивает детали билета и возвращает валидированный Result."""
    details_payload = {"Number": ticket_number, "Lang": LANG_RUS}
    attach_json(details_payload, f"ticket_details_payload_{ticket_number}")
    details_response = user_tickets_client.get_ticket_details(details_payload)
    attach_response(details_response, f"ticket_details_response_{ticket_number}")

    assert_ok_json(details_response, "tickets/details")

    details_data = TicketDetailsResponse(**details_response.json())
    assert details_data.Error is None
    assert details_data.Result is not None
    return details_data.Result


def _annul_ticket(user_tickets_client, ticket_number: str, ticket_id):
    annulation_payload = {
        "TicketNumber": ticket_number,
        "TicketId": ticket_id,
        "Lang": LANG_RUS,
    }
    attach_json(annulation_payload, f"annulation_payload_{ticket_number}")
    annulation_response = user_tickets_client.annulation(annulation_payload)
    attach_response(annulation_response, f"annulation_response_{ticket_number}")

    assert_ok_json(annulation_response, f"tickets/annulation (билет {ticket_number})")

    annulation_data = TicketAnnulationResponse(**annulation_response.json())
    assert annulation_data.Error is None
    assert annulation_data.Result is True, f"Аннуляция билета {ticket_number} не выполнена"


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
    routes_client,
    user_tickets_client,
    alphabank_client,
    user_place_cleanup,
):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    _, route_id, search_id = search_route_for_carrier(routes_client, carrier, valid_booking_depart_date)

    route_details = get_route_details(routes_client, route_id, search_id, valid_booking_depart_date)
    assert route_details.free_bus_places, "Свободные места не найдены"

    first_place = route_details.free_bus_places[0]
    tariff_id = pick_tariff_id(route_details)
    attach_text(first_place, "first_place")
    if tariff_id is not None:
        attach_text(tariff_id, "tariff_id")

    select_place_payload = {
        "NumberPlace": first_place,
        "RouteId": str(route_id),
        "SearchId": str(search_id),
        "Lang": LANG_RUS,
    }
    select_place_ok(user_tickets_client, select_place_payload)
    user_place_cleanup.track(select_place_payload)

    booking_payload = build_booking_payload(
        route_id=route_id,
        search_id=search_id,
        place_number=first_place,
        tariff_id=tariff_id,
    )
    _, ticket_numbers, md_order = _do_user_booking(user_tickets_client, booking_payload)
    user_place_cleanup.places_booked()

    ticket_number_list = ticket_numbers if isinstance(ticket_numbers, list) else [ticket_numbers]

    process_payment(alphabank_client, md_order)

    _assert_tickets_exist(user_tickets_client, ticket_number_list)

    with allure.step("Get Tickets"):
        get_tickets_payload = {
            "Page": 1,
            "PageSize": 10,
            "UserId": None,
            "Status": 0,
            "Lang": LANG_RUS,
        }
        attach_json(get_tickets_payload, "get_tickets_payload")
        get_tickets_response = user_tickets_client.get_tickets(get_tickets_payload)
        attach_response(get_tickets_response, "get_tickets_response")

        assert_ok_json(get_tickets_response, "tickets/get")

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

        first_ticket = tickets_data.Result.Collections[0]
        attach_text(first_ticket.TicketNumber, "first_ticket_number")
        attach_text(first_ticket.PdfUrl, "first_ticket_pdf_url")

    with allure.step("Get Ticket Details"):
        details = _get_ticket_details(user_tickets_client, ticket_number_list[0])
        passenger = booking_payload["Passengers"][0]
        assert_ticket_details_match(details, passenger, booking_payload, carrier, ticket_number_list[0])

    with allure.step("Annulation"):
        _annul_ticket(user_tickets_client, details.TicketNumber, details.Id)


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
    routes_client,
    user_tickets_client,
    alphabank_client,
    user_place_cleanup,
):
    carrier = carrier_booking_context
    valid_booking_depart_date = carrier["date"]

    _, route_id, search_id = search_route_for_carrier(routes_client, carrier, valid_booking_depart_date)

    route_details = get_route_details(routes_client, route_id, search_id, valid_booking_depart_date)

    free_places = route_details.free_bus_places
    if len(free_places) < 2:
        pytest.skip("Недостаточно свободных мест для теста (нужно минимум 2)")

    place_1, place_2 = free_places[0], free_places[1]
    tariff_id = pick_tariff_id(route_details)
    attach_text(f"{place_1}, {place_2}", "selected_places")

    for index, place in enumerate([place_1, place_2], start=1):
        select_payload = {
            "NumberPlace": place,
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        select_place_ok(user_tickets_client, select_payload, step_name=f"Select Place {index}")
        user_place_cleanup.track(select_payload)

    booking_payload = build_booking_payload(
        route_id=route_id,
        search_id=search_id,
        place_number=[place_1, place_2],
        tariff_id=tariff_id,
    )
    _, ticket_numbers, md_order = _do_user_booking(
        user_tickets_client, booking_payload, step_name="User Booking (2 билета)"
    )
    user_place_cleanup.places_booked()

    assert isinstance(ticket_numbers, list), (
        f"TicketsNumber должен быть списком при бронировании нескольких мест, получен: {type(ticket_numbers)}"
    )
    assert len(ticket_numbers) == 2, f"Ожидалось 2 билета, получено {len(ticket_numbers)}"

    process_payment(alphabank_client, md_order)

    _assert_tickets_exist(user_tickets_client, ticket_numbers)

    with allure.step("Get Tickets"):
        get_tickets_payload = {
            "Page": 1,
            "PageSize": 10,
            "UserId": None,
            "Status": 0,
            "Lang": LANG_RUS,
        }
        attach_json(get_tickets_payload, "get_tickets_payload")
        get_tickets_response = user_tickets_client.get_tickets(get_tickets_payload)
        attach_response(get_tickets_response, "get_tickets_response")

        assert_ok_json(get_tickets_response, "tickets/get")

        tickets_data = TicketsListResponse(**get_tickets_response.json())
        assert tickets_data.Error is None
        assert tickets_data.Result is not None
        assert tickets_data.Result.Count is not None and tickets_data.Result.Count >= 2
        assert tickets_data.Result.Collections, "Список билетов пустой"

    with allure.step("Get Ticket Details (оба билета)"):
        seat_to_passenger = {p["PlaceNumber"]: p for p in booking_payload["Passengers"]}
        ticket_ids: dict[str, int] = {}

        for ticket_number in ticket_numbers:
            details = _get_ticket_details(user_tickets_client, ticket_number)
            passenger = seat_to_passenger.get(details.PlaceDepart)
            assert passenger is not None, (
                f"Не найден пассажир для места {details.PlaceDepart} у билета {ticket_number}"
            )
            assert_ticket_details_match(details, passenger, booking_payload, carrier, ticket_number)
            ticket_ids[ticket_number] = details.Id

    with allure.step("Annulation (оба билета)"):
        for ticket_number in ticket_numbers:
            _annul_ticket(user_tickets_client, ticket_number, ticket_ids[ticket_number])
