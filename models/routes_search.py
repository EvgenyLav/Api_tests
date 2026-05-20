from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class City(BaseModel):
    NameRus: str


class Route(BaseModel):
    City1: City
    City2: City


class RouteGroup(BaseModel):
    Id: int | str | None = None
    DateDepart: str
    Routes: List[Route] = Field(default_factory=list)

    @property
    def departure_date(self) -> str:
        return datetime.strptime(self.DateDepart, "%d.%m.%Y").strftime("%Y-%m-%d")


class CarrierRoute(BaseModel):
    CarrierId: int | None = None
    IsActive: bool | None = None
    Routes: List[RouteGroup] = Field(default_factory=list)


class SearchResult(BaseModel):
    CityDeparture: int
    CityArrival: int
    Id: int | str
    CarrierRoutes: List[CarrierRoute] = Field(default_factory=list)

    @property
    def all_routes(self) -> List[Route]:
        routes: List[Route] = []
        for carrier in self.CarrierRoutes:
            for route_group in carrier.Routes:
                routes.extend(route_group.Routes)
        return routes

    @property
    def first_route_group(self) -> RouteGroup:
        for carrier in self.CarrierRoutes:
            if carrier.Routes:
                return carrier.Routes[0]
        raise ValueError("No route groups found")

    def route_group_by_carrier(self, carrier_id: int) -> RouteGroup | None:
        for carrier in self.CarrierRoutes:
            if carrier.CarrierId == carrier_id and carrier.Routes:
                return carrier.Routes[0]
        return None

    @property
    def has_routes(self) -> bool:
        return any(carrier.Routes for carrier in self.CarrierRoutes)


class RoutesSearchResponse(BaseModel):
    Result: SearchResult
