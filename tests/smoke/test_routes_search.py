import pytest
import allure

from models.routes_search import RoutesSearchResponse
from tests.helpers import assert_ok_json, attach_json, attach_response, attach_text
from utils.constants import MINSK, MOSCOW, MINSK_NAME, MOSCOW_NAME


@allure.feature("Routes Search API")
@allure.story("Smoke tests")
@pytest.mark.smoke
@pytest.mark.routes
def test_routes_search(routes_client, valid_depart_date):
    payload = {
        "CityDeparture": MOSCOW,
        "CityArrival": MINSK,
        "DateDeparture": valid_depart_date,
    }

    with allure.step("Отправка запроса на /routes/search"):
        attach_json(payload, "search_routes_payload")
        response = routes_client.search_routes(payload)
        attach_response(response, "search_routes_response")

    with allure.step("Проверка статуса ответа и формата JSON"):
        assert_ok_json(response, "routes/search")

    data = RoutesSearchResponse(**response.json())

    with allure.step("Проверка CityDeparture и CityArrival"):
        assert data.Result.CityDeparture == MOSCOW
        assert data.Result.CityArrival == MINSK

    with allure.step("Проверка маршрутов"):
        assert data.Result.all_routes, "Маршруты не найдены"

        for route in data.Result.all_routes:
            assert route.City1.NameRus == MOSCOW_NAME
            assert route.City2.NameRus == MINSK_NAME

    with allure.step("Проверка SEARCHID"):
        assert data.Result.Id is not None
        attach_text(data.Result.Id, "search_id")

    with allure.step("Проверка даты отправления"):
        assert data.Result.first_route_group.departure_date == valid_depart_date
