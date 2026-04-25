from api.base import BaseClient


class RoutesClient(BaseClient):
    SEARCH = "/routes/search"
    GET_SEARCH = "/routes/getSearch"
    GET_ROUTE = "/routes/getRoute"
    GET_TARIFFS = "/routes/getTariffs"

    def search_routes(self, payload: dict):
        return self.post(self.SEARCH, json=payload)

    def get_search(self, payload: dict):
        return self.post(self.GET_SEARCH, json=payload)

    def get_route(self, payload: dict):
        return self.post(self.GET_ROUTE, json=payload)

    def get_tariffs(self, payload: dict):
        return self.post(self.GET_TARIFFS, json=payload)
