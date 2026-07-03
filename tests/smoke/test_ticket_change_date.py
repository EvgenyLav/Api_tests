import allure
import pytest

from models.user_booking import ChangeDateResponse, ChangeDateSubmitResponse
from tests.helpers import (
    assert_ok_json,
    attach_json,
    attach_response,
    attach_text,
    get_route_details,
    get_ticket_details_ok,
    get_valid_date,
    search_route_for_carrier,
    select_place_ok,
)
from utils.constants import CARRIER_CONFIGS, LANG_RUS


@allure.feature("Booking API")
@allure.story("Ticket change date flow")
@pytest.mark.smoke
@pytest.mark.booking
@pytest.mark.parametrize(
    "carrier_booking_context",
    CARRIER_CONFIGS,
    indirect=True,
    ids=[c["name"] for c in CARRIER_CONFIGS],
)
def test_ticket_change_date_flow(
    carrier_booking_context,
    user_booked_ticket,
    routes_client,
    user_tickets_client,
    user_place_cleanup,
):
    carrier = carrier_booking_context
    ticket = user_booked_ticket

    with allure.step("Get Ticket Details (исходный билет)"):
        details = get_ticket_details_ok(user_tickets_client, ticket["ticket_number"])
        assert details.HasAbilityChangeDate is True, (
            f"Смена даты недоступна для билета {ticket['ticket_number']}"
        )
        original_date_depart = details.DateDepart
        attach_text(original_date_depart, "original_date_depart")

    with allure.step("Поиск маршрута на новую дату"):
        new_date = get_valid_date(
            routes_client,
            city_departure=carrier["departure"],
            city_arrival=carrier["arrival"],
            carrier_id=carrier["carrier_id"],
            days_ahead=7,
            exclude_dates={ticket["date"]},
        )
        attach_text(new_date, "new_date")

    _, new_route_id, new_search_id = search_route_for_carrier(routes_client, carrier, new_date)

    new_route_details = get_route_details(routes_client, new_route_id, new_search_id, new_date)
    assert new_route_details.free_bus_places, "Нет свободных мест на новую дату"
    new_place = new_route_details.free_bus_places[0]
    attach_text(new_place, "new_place")

    select_payload = {
        "NumberPlace": new_place,
        "RouteId": str(new_route_id),
        "SearchId": str(new_search_id),
        "Lang": LANG_RUS,
    }
    select_place_ok(user_tickets_client, select_payload, step_name="Select Place (новая дата)")
    user_place_cleanup.track(select_payload)

    with allure.step("Change Date"):
        change_date_payload = {
            "TicketNumber": ticket["ticket_number"],
            "TicketId": ticket["ticket_id"],
            "PlaceNumber": new_place,
            "SiteVersionId": 2,
            "RouteId": str(new_route_id),
            "SearchId": str(new_search_id),
            "Lang": LANG_RUS,
        }
        attach_json(change_date_payload, "change_date_payload")
        change_date_response = user_tickets_client.change_date(change_date_payload)
        attach_response(change_date_response, "change_date_response")

        assert_ok_json(change_date_response, "tickets/changedate")

        change_date_data = ChangeDateResponse(**change_date_response.json())
        assert change_date_data.Error is None, (
            f"tickets/changedate вернул ошибку: {change_date_response.text}"
        )
        assert change_date_data.Result is not None, (
            f"Пустой Result в ответе tickets/changedate: {change_date_response.text}"
        )

        order_id = (
            change_date_data.Result.Data.OrderId
            if change_date_data.Result.Data is not None
            else None
        )
        assert order_id is not None, (
            f"OrderId не найден в ответе tickets/changedate: {change_date_response.text}"
        )
        attach_text(order_id, "change_date_order_id")

    with allure.step("Change Date Submit"):
        submit_payload = {
            "TicketNumber": ticket["ticket_number"],
            "TicketId": ticket["ticket_id"],
            "OrderId": str(order_id),
            "Lang": LANG_RUS,
        }
        attach_json(submit_payload, "change_date_submit_payload")
        submit_response = user_tickets_client.change_date_submit(submit_payload)
        attach_response(submit_response, "change_date_submit_response")

        assert_ok_json(submit_response, "tickets/changedate/submit")

        submit_data = ChangeDateSubmitResponse(**submit_response.json())
        assert submit_data.Error is None, (
            f"tickets/changedate/submit вернул ошибку: {submit_response.text}"
        )
        user_place_cleanup.places_booked()

    with allure.step("Проверка новой даты в деталях билета"):
        updated_details = get_ticket_details_ok(user_tickets_client, ticket["ticket_number"])
        attach_text(updated_details.DateDepart, "updated_date_depart")

        assert updated_details.DateDepart, "DateDepart пустой после смены даты"
        assert updated_details.DateDepart != original_date_depart, (
            f"Дата поездки не изменилась: '{updated_details.DateDepart}'"
        )
        assert updated_details.PlaceDepart == new_place, (
            f"Место не совпадает: ожидалось {new_place}, получено {updated_details.PlaceDepart}"
        )
