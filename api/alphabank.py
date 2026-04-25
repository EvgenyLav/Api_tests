from api.base import BaseClient


class AlphaBankClient(BaseClient):
    STATUS = "/alphabank/status"
    CREATE = "/alphabank/create"
    IS_CREATED = "/alphabank/iscreated"

    def get_status(self, payload: dict):
        return self.post(self.STATUS, json=payload)

    def create_ticket(self, payload: dict):
        return self.post(self.CREATE, json=payload)

    def is_created(self, payload: dict):
        return self.post(self.IS_CREATED, json=payload)
