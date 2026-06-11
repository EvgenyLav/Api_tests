import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import pytest
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.alphabank import AlphaBankClient
from api.routes import RoutesClient
from api.tickets import TicketsClient
from config.settings import BASE_URL
from models.booking_flow import GetRouteResponse
from models.routes_search import RoutesSearchResponse
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


def get_valid_date(routes_client, city_departure, city_arrival, carrier_id=None, days_ahead=5):
    for i in range(1, days_ahead + 1):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")

        payload = {
            "CityDeparture": city_departure,
            "CityArrival": city_arrival,
            "DateDeparture": date,
        }

        response = routes_client.search_routes(payload)
        data = RoutesSearchResponse(**response.json())

        if carrier_id is not None:
            if data.Result.route_group_by_carrier(carrier_id) is not None:
                return date
        elif data.Result.has_routes:
            return date

    pytest.skip("Нет маршрутов на ближайшие даты")


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
