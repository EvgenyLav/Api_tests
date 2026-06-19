import pytest
import allure
import json

from models.routes_search import RoutesSearchResponse
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
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2),
            name="search_routes_payload",
            attachment_type=allure.attachment_type.JSON,
        )
        response = routes_client.search_routes(payload)
        allure.attach(
            response.text,
            name="search_routes_response",
            attachment_type=allure.attachment_type.JSON,
        )

    with allure.step("Проверка статуса ответа и формата JSON"):
        assert response.status_code in range(200, 300)
        assert response.headers["Content-Type"].startswith("application/json")

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
        allure.attach(str(data.Result.Id), name="search_id", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Проверка даты отправления"):
        assert data.Result.first_route_group.departure_date == valid_depart_date
