import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.alphabank import AlphaBankClient
from api.auth import AuthClient
from api.routes import RoutesClient
from api.tickets import TicketsClient
from config.settings import BASE_URL, ROOT_URL, USER_LOGIN, USER_PASSWORD
from models.user_booking import TokenResponse
from models.booking_flow import GetRouteResponse
from models.routes_search import RoutesSearchResponse
from tests.builders.booking import build_booking_payload
from tests.helpers import (
    PlaceCleanup,
    book_first_place,
    get_route_details,
    get_ticket_details_ok,
    get_valid_date,
    pick_tariff_id,
    process_payment,
    search_route_for_carrier,
    user_booking_ok,
)
from utils.constants import MINSK, MOSCOW, CARRIER_CONFIGS, LANG_RUS


@pytest.fixture
def routes_client():
    return RoutesClient(base_url=BASE_URL)


@pytest.fixture
def tickets_client():
    return TicketsClient(base_url=BASE_URL)


@pytest.fixture
def alphabank_client():
    return AlphaBankClient(base_url=BASE_URL)


@pytest.fixture(scope="session")
def token_data():
    client = AuthClient(base_url=ROOT_URL)
    return TokenResponse(**client.get_token(USER_LOGIN, USER_PASSWORD))


@pytest.fixture(scope="session")
def user_tickets_client(token_data):
    client = TicketsClient(base_url=BASE_URL)
    client.session.headers.update({"Authorization": f"Bearer {token_data.access_token}"})
    return client


@pytest.fixture
def place_cleanup(tickets_client):
    """Снимает выбранные места, если анонимный тест упал до брони."""
    cleanup = PlaceCleanup(tickets_client)
    yield cleanup
    cleanup.finalize()


@pytest.fixture
def user_place_cleanup(user_tickets_client):
    """Снимает выбранные места, если пользовательский тест упал до брони."""
    cleanup = PlaceCleanup(user_tickets_client)
    yield cleanup
    cleanup.finalize()


@pytest.fixture
def user_booked_ticket(
    carrier_booking_context,
    routes_client,
    user_tickets_client,
    alphabank_client,
    user_place_cleanup,
):
    """Прекондишен: бронирует и создаёт один билет под пользователем.

    Возвращает dict с ticket_number/ticket_id/booking_payload/carrier.
    В teardown аннулирует билет best-effort (тест мог поменять номер —
    аннулируем по актуальному значению из dict).
    """
    carrier = carrier_booking_context
    if not carrier["issues_tickets"]:
        pytest.skip(f"Стенд не выпускает билеты перевозчика '{carrier['name']}' — оплатный флоу недоступен")

    _, route_id, search_id = search_route_for_carrier(routes_client, carrier, carrier["date"])
    route_details = get_route_details(routes_client, route_id, search_id, carrier["date"])

    place = book_first_place(
        user_tickets_client, route_details, route_id, search_id, user_place_cleanup
    )

    booking_payload = build_booking_payload(
        route_id=route_id,
        search_id=search_id,
        place_number=place,
        tariff_id=pick_tariff_id(route_details),
        document_id=carrier["document_id"],
    )
    _, ticket_numbers, md_order = user_booking_ok(user_tickets_client, booking_payload)
    user_place_cleanup.places_booked()

    process_payment(alphabank_client, md_order)

    ticket_number = ticket_numbers[0] if isinstance(ticket_numbers, list) else ticket_numbers
    details = get_ticket_details_ok(user_tickets_client, ticket_number)

    ticket = {
        "ticket_number": ticket_number,
        "ticket_id": details.Id,
        "booking_payload": booking_payload,
        "carrier": carrier,
        "date": carrier["date"],
    }
    yield ticket

    try:
        current = get_ticket_details_ok(user_tickets_client, ticket["ticket_number"])
        if current.HasAbilityAnnulationTicket:
            user_tickets_client.annulation({
                "TicketNumber": ticket["ticket_number"],
                "TicketId": current.Id,
                "Lang": LANG_RUS,
            })
    except Exception:
        pass


@pytest.fixture
def valid_depart_date(routes_client):
    return get_valid_date(routes_client, city_departure=MOSCOW, city_arrival=MINSK)


@pytest.fixture
def carrier_booking_context(request, routes_client):
    carrier = request.param
    date = get_valid_date(
        routes_client,
        city_departure=carrier["departure"],
        city_arrival=carrier["arrival"],
        carrier_id=carrier["carrier_id"],
    )
    return {**carrier, "date": date}


@pytest.fixture
def selected_place_context(carrier_booking_context, routes_client, tickets_client):
    """Searches a route, selects the first free place, yields context, then removes the place."""
    carrier = carrier_booking_context

    search_data = RoutesSearchResponse(
        **routes_client.search_routes({
            "CityDeparture": carrier["departure"],
            "CityArrival": carrier["arrival"],
            "DateDeparture": carrier["date"],
        }).json()
    )
    route_group = search_data.Result.route_group_by_carrier(carrier["carrier_id"])
    assert route_group is not None, f"Маршруты агрегатора '{carrier['name']}' не найдены"
    route_id = route_group.Id
    search_id = search_data.Result.Id

    route_data = GetRouteResponse(
        **routes_client.get_route({
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }).json()
    )
    route_details = route_data.Result.Route
    if not route_details.has_seat_map:
        pytest.skip(f"У перевозчика '{carrier['name']}' свободная рассадка — выбор места не применим")
    assert route_details.free_bus_places, "Нет свободных мест для теста"

    place_number = route_details.free_bus_places[0]
    tariff_id = next((t.Id for t in route_details.Tariffs if t.Id is not None), None)

    select_payload = {
        "NumberPlace": place_number,
        "RouteId": str(route_id),
        "SearchId": str(search_id),
        "Lang": LANG_RUS,
    }
    select_response = tickets_client.select_place(select_payload)
    assert select_response.status_code in range(200, 300), \
        f"select_place failed in fixture: {select_response.text}"

    yield {
        "route_id": route_id,
        "search_id": search_id,
        "place_number": place_number,
        "tariff_id": tariff_id,
        "select_payload": select_payload,
        "carrier": carrier,
    }

    tickets_client.remove_place(select_payload)
