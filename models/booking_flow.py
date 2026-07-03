import re
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, model_validator


class ApiError(BaseModel):
    Message: str | None = None


class Price(BaseModel):
    CurrencyName: str


class Tariff(BaseModel):
    Id: int | None = None
    Name: str
    Prices: List[Price] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def populate_id_from_value(cls, data):
        if isinstance(data, dict) and data.get("Id") is None and data.get("Value") is not None:
            data = data.copy()
            data["Id"] = data["Value"]
        return data


class BusPlace(BaseModel):
    Seat: int
    IsFree: bool


class RouteSegment(BaseModel):
    Tariffs: List[Tariff] = Field(default_factory=list)


class RouteDetails(BaseModel):
    Id: int | str
    City1: str
    City2: str
    DateDepart: str
    Routes: List[RouteSegment] = Field(default_factory=list)
    # None — у перевозчика нет схемы мест (свободная рассадка), выбор места не применим
    FullBusPlaces: List[BusPlace] | None = None

    @property
    def first_segment(self) -> RouteSegment | None:
        return self.Routes[0] if self.Routes else None

    @property
    def Tariffs(self) -> List[Tariff]:
        if not self.first_segment:
            return []
        return self.first_segment.Tariffs

    @property
    def departure_date(self) -> str:
        return datetime.strptime(self.DateDepart, "%d.%m.%Y").strftime("%Y-%m-%d")

    @property
    def has_seat_map(self) -> bool:
        return self.FullBusPlaces is not None

    @property
    def free_bus_places(self) -> List[int]:
        return [place.Seat for place in self.FullBusPlaces or [] if place.IsFree]


class GetRouteResult(BaseModel):
    Route: RouteDetails


class GetRouteResponse(BaseModel):
    Result: GetRouteResult
    Error: ApiError | None = None


class GetTariffsResponse(BaseModel):
    Result: List[Tariff] = Field(default_factory=list)
    Error: ApiError | None = None


class SelectPlaceResult(BaseModel):
    Success: bool


class SelectPlaceResponse(BaseModel):
    Result: SelectPlaceResult
    Error: ApiError | None = None


class RemovePlaceResponse(BaseModel):
    Result: bool
    Error: ApiError | None = None


class BookingData(BaseModel):
    OrderId: int | str | None = None
    TicketsNumber: str | List[str] | None = None


class BookingGatewayResult(BaseModel):
    Response: str | None = None
    Data: BookingData | None = None


class BookingResult(BaseModel):
    PaymentUrl: str
    result: BookingGatewayResult | None = None

    @property
    def md_order(self) -> str | None:
        if not self.result or not self.result.Response:
            return None
        match = re.search(r"mdOrder=([a-zA-Z0-9-]+)", self.result.Response)
        return match.group(1) if match else None


class BookingResponse(BaseModel):
    Result: BookingResult | None = None
    Error: ApiError | None = None


class PaymentStatusResult(BaseModel):
    Success: bool
    Status: str


class PaymentStatusResponse(BaseModel):
    Result: PaymentStatusResult
    Error: ApiError | None = None


class CreateTicketResult(BaseModel):
    Success: bool
    Data: bool
    Error: str | None = None
    ExtraData: str | None = None
    ErrorType: int | None = None


class CreateTicketResponse(BaseModel):
    Result: CreateTicketResult
    Error: ApiError | None = None


class IsCreatedResponse(BaseModel):
    Result: CreateTicketResult | bool | None
    Error: ApiError | None = None
