import sys
from pathlib import Path

import pytest
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.alphabank import AlphaBankClient
from api.routes import RoutesClient
from api.tickets import TicketsClient
from config.settings import BASE_URL
from models.routes_search import RoutesSearchResponse
from utils.constants import MINSK, MOSCOW, CARRIER_CONFIGS


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
