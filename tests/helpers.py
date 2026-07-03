import json
from datetime import datetime, timedelta

import allure
import pytest

from models.booking_flow import (
    CreateTicketResponse,
    CreateTicketResult,
    GetRouteResponse,
    IsCreatedResponse,
    PaymentStatusResponse,
    SelectPlaceResponse,
)
from models.routes_search import RoutesSearchResponse
from models.user_booking import (
    TicketAnnulationResponse,
    TicketDetailsResponse,
    UserBookingResponse,
)
from tests.builders.alphabank import build_status_payload, build_validation_payload
from utils.constants import LANG_RUS


def attach_json(data, name: str):
    allure.attach(
        json.dumps(data, ensure_ascii=False, indent=2),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def attach_response(response, name: str):
    allure.attach(response.text, name=name, attachment_type=allure.attachment_type.JSON)


def attach_text(value, name: str):
    allure.attach(str(value), name=name, attachment_type=allure.attachment_type.TEXT)


def assert_ok_json(response, context: str = ""):
    prefix = f"{context}: " if context else ""
    assert 200 <= response.status_code < 300, (
        f"{prefix}ожидался успешный статус, получен {response.status_code}. Body: {response.text}"
    )
    assert response.headers["Content-Type"].startswith("application/json"), (
        f"{prefix}ожидался application/json, получен {response.headers.get('Content-Type')}"
    )


def get_valid_date(
    routes_client,
    city_departure: int,
    city_arrival: int,
    carrier_id: int | None = None,
    days_ahead: int = 5,
    exclude_dates: set[str] | None = None,
) -> str:
    """Ищет ближайшую дату с маршрутами (опционально — конкретного перевозчика, минуя exclude_dates)."""
    exclude_dates = exclude_dates or set()
    for i in range(1, days_ahead + 1):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        if date in exclude_dates:
            continue

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


def search_route_for_carrier(routes_client, carrier: dict, date: str):
    """Шаг Search Routes: ищет маршруты и возвращает (search_data, route_id, search_id)."""
    with allure.step("Search Routes"):
        payload = {
            "CityDeparture": carrier["departure"],
            "CityArrival": carrier["arrival"],
            "DateDeparture": date,
        }
        attach_json(payload, "search_routes_payload")
        response = routes_client.search_routes(payload)
        attach_response(response, "search_routes_response")

        assert_ok_json(response, "routes/search")

        search_data = RoutesSearchResponse(**response.json())
        assert search_data.Result.CityDeparture == carrier["departure"]
        assert search_data.Result.CityArrival == carrier["arrival"]
        assert search_data.Result.Id is not None
        assert search_data.Result.all_routes, "Маршруты не найдены"

        route_group = search_data.Result.route_group_by_carrier(carrier["carrier_id"])
        assert route_group is not None, f"Маршруты агрегатора '{carrier['name']}' не найдены"
        assert route_group.departure_date == date

        route_id = route_group.Id
        search_id = search_data.Result.Id
        assert route_id is not None, "Id маршрута не найден в ответе routes/search"
        attach_text(search_id, "search_id")
        attach_text(route_id, "route_id")

    return search_data, route_id, search_id


def get_route_details(routes_client, route_id, search_id, expected_date: str):
    """Шаг Get Route: возвращает RouteDetails с базовыми проверками (свободные места проверяет вызывающий)."""
    with allure.step("Get Route"):
        payload = {
            "RouteId": str(route_id),
            "SearchId": str(search_id),
            "Lang": LANG_RUS,
        }
        attach_json(payload, "get_route_payload")
        response = routes_client.get_route(payload)
        attach_response(response, "get_route_response")

        assert_ok_json(response, "routes/getRoute")

        route_details = GetRouteResponse(**response.json()).Result.Route
        assert str(route_details.Id) == str(route_id)
        assert route_details.City1 and route_details.City2
        assert route_details.Tariffs, "Тарифы маршрута не найдены"
        assert route_details.FullBusPlaces, "FullBusPlaces пустой"
        assert route_details.departure_date == expected_date

    return route_details


def pick_tariff_id(route_details) -> int | None:
    return next((t.Id for t in route_details.Tariffs if t.Id is not None), None)


def select_place_ok(tickets_client, payload: dict, step_name: str = "Select Place"):
    """Выбирает место и проверяет Success. Возвращает response."""
    with allure.step(step_name):
        attach_json(payload, "select_place_payload")
        response = tickets_client.select_place(payload)
        attach_response(response, "select_place_response")

        assert_ok_json(response, "tickets/selectplace")
        assert SelectPlaceResponse(**response.json()).Result.Success is True

    return response


def user_booking_ok(user_tickets_client, booking_payload: dict, step_name: str = "User Booking"):
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


def get_ticket_details_ok(user_tickets_client, ticket_number: str):
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


def annul_ticket_ok(user_tickets_client, ticket_number: str, ticket_id):
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


def assert_ticket_created(is_created_data: IsCreatedResponse, context: str = "Билет не создан"):
    result = is_created_data.Result
    assert (
        (isinstance(result, CreateTicketResult) and result.Success is True)
        or result is True
    ), f"{context}: Result={result}"


def process_payment(alphabank_client, md_order: str):
    """Платёжный цикл: Get Status -> Create Ticket -> Is Created."""
    status_payload = build_status_payload(md_order)
    validation_payload = build_validation_payload(md_order)

    with allure.step("Get Status"):
        attach_json(status_payload, "get_status_payload")
        get_status_response = alphabank_client.get_status(status_payload)
        attach_response(get_status_response, "get_status_response")

        assert_ok_json(get_status_response, "alphabank/status")

        status_data = PaymentStatusResponse(**get_status_response.json())
        assert status_data.Result.Success is False
        assert status_data.Result.Status.startswith("0:"), (
            f"Ожидался статус '0: ...' (заказ зарегистрирован, не оплачен), получен '{status_data.Result.Status}'"
        )
        assert status_data.Error is None

    with allure.step("Create Ticket"):
        attach_json(validation_payload, "create_ticket_payload")
        create_ticket_response = alphabank_client.create_ticket(validation_payload)
        attach_response(create_ticket_response, "create_ticket_response")

        assert_ok_json(create_ticket_response, "alphabank/create")

        create_ticket_data = CreateTicketResponse(**create_ticket_response.json())
        assert create_ticket_data.Result.Success is True
        assert create_ticket_data.Result.Data is True
        assert create_ticket_data.Error is None

    with allure.step("Is Created"):
        attach_json(validation_payload, "is_created_payload")
        is_created_response = alphabank_client.is_created(validation_payload)
        attach_response(is_created_response, "is_created_response")

        assert_ok_json(is_created_response, "alphabank/iscreated")

        is_created_data = IsCreatedResponse(**is_created_response.json())
        assert is_created_data.Error is None
        assert_ticket_created(is_created_data)


def assert_ticket_details_match(d, passenger: dict, booking_payload: dict, carrier: dict, ticket_number: str):
    """Сверяет детали билета с данными пассажира и брони."""
    assert d.TicketNumber == ticket_number, (
        f"TicketNumber в деталях не совпадает с запрошенным: {ticket_number}"
    )
    assert d.ClientName, f"ClientName пустой у билета {ticket_number}"
    for name_part in [passenger["LastName"], passenger["FirstName"], passenger["MiddleName"]]:
        assert name_part.upper() in d.ClientName.upper(), (
            f"'{name_part}' не найден в ClientName '{d.ClientName}' (билет {ticket_number})"
        )
    assert d.Email == booking_payload["Email"], (
        f"Email не совпадает у билета {ticket_number}: ожидался '{booking_payload['Email']}'"
    )
    assert d.ClientCitizenship == passenger["Citizenship"], f"Citizenship не совпадает у билета {ticket_number}"
    assert d.ClientPasport == passenger["DocumentNumber"], f"Номер документа не совпадает у билета {ticket_number}"
    assert d.ClientDateOfBirthDay is not None and d.ClientDateOfBirthDay.startswith(passenger["Birthdate"]), (
        f"Дата рождения не совпадает у билета {ticket_number}: "
        f"ожидалась '{passenger['Birthdate']}', получена '{d.ClientDateOfBirthDay}'"
    )
    assert d.TarifId == passenger["TarifId"], f"TarifId не совпадает у билета {ticket_number}"
    assert d.PlaceDepart == passenger["PlaceNumber"], (
        f"PlaceDepart не совпадает у билета {ticket_number}: ожидалось {passenger['PlaceNumber']}"
    )
    assert d.CityDepartId == carrier["departure"], f"CityDepartId не совпадает у билета {ticket_number}"
    assert d.CityArriveId == carrier["arrival"], f"CityArriveId не совпадает у билета {ticket_number}"
    assert d.PhoneNumber, f"PhoneNumber пустой у билета {ticket_number}"
    assert d.DateDepart, f"DateDepart пустой у билета {ticket_number}"
    assert d.PriceTicket is not None and d.PriceTicket > 0, f"PriceTicket некорректный у билета {ticket_number}"
    assert d.CurrencyName, f"CurrencyName пустой у билета {ticket_number}"
    assert d.PdfUrl, f"PdfUrl пустой у билета {ticket_number}"
    assert d.RouteDepart is not None, f"RouteDepart отсутствует у билета {ticket_number}"
    assert d.RouteDepart.DepartTime, f"DepartTime пустой у билета {ticket_number}"
    assert d.RouteDepart.ArriveTime, f"ArriveTime пустой у билета {ticket_number}"
    assert d.RouteDepart.DepartPoint is not None, f"DepartPoint отсутствует у билета {ticket_number}"
    assert d.RouteDepart.DepartPoint.Name, f"DepartPoint.Name пустой у билета {ticket_number}"
    assert d.RouteDepart.ArrivePoint is not None, f"ArrivePoint отсутствует у билета {ticket_number}"
    assert d.RouteDepart.ArrivePoint.Name, f"ArrivePoint.Name пустой у билета {ticket_number}"
    assert d.HasAbilityChangeDate is not None, f"HasAbilityChangeDate отсутствует у билета {ticket_number}"
    assert d.HasAbilityAnnulationTicket is True, f"Аннуляция недоступна для билета {ticket_number}"


class PlaceCleanup:
    """Best-effort снятие выбранных мест в teardown, если тест упал до брони.

    Билеты в teardown не аннулируем: билет появляется только после alphabank/create,
    а в happy path сразу за ним идёт аннуляция обычным шагом теста.
    """

    def __init__(self, tickets_client):
        self.client = tickets_client
        self.place_payloads: list[dict] = []

    def track(self, payload: dict):
        self.place_payloads.append(payload)

    def untrack(self, payload: dict):
        if payload in self.place_payloads:
            self.place_payloads.remove(payload)

    def places_booked(self):
        """Места выкуплены бронью — remove_place больше не применим."""
        self.place_payloads.clear()

    def finalize(self):
        for payload in self.place_payloads:
            try:
                self.client.remove_place(payload)
            except Exception:
                pass
