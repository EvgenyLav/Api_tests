from api.base import BaseClient


class TicketsClient(BaseClient):
    SELECT_PLACE = "/tickets/selectplace"
    REMOVE_PLACE = "/tickets/removeplace"
    BOOKING = "/tickets/booking"
    USER_BOOKING = "/tickets/user/booking"
    GET = "/tickets/get"
    DETAILS = "/tickets/details"
    EXISTS = "/tickets/exists"
    GET_BLANKS = "/tickets/getTicketBlanks"

    def select_place(self, payload: dict):
        return self.post(self.SELECT_PLACE, json=payload)

    def remove_place(self, payload: dict):
        return self.post(self.REMOVE_PLACE, json=payload)

    def booking(self, payload: dict):
        return self.post(self.BOOKING, json=payload)

    def user_booking(self, payload: dict):
        return self.post(self.USER_BOOKING, json=payload)

    def get_tickets(self, payload: dict):
        return self.post(self.GET, json=payload)

    def get_ticket_details(self, payload: dict):
        return self.post(self.DETAILS, json=payload)

    def ticket_exists(self, payload: dict):
        return self.post(self.EXISTS, json=payload)

    def get_ticket_blanks(self, payload: dict):
        return self.post(self.GET_BLANKS, json=payload)
