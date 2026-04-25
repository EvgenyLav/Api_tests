from api.base import BaseClient


class TicketsClient(BaseClient):
    SELECT_PLACE = "/tickets/selectplace"
    REMOVE_PLACE = "/tickets/removeplace"
    BOOKING = "/tickets/booking"

    def select_place(self, payload: dict):
        return self.post(self.SELECT_PLACE, json=payload)

    def remove_place(self, payload: dict):
        return self.post(self.REMOVE_PLACE, json=payload)

    def booking(self, payload: dict):
        return self.post(self.BOOKING, json=payload)
