import re
from typing import Any, List
from pydantic import BaseModel, ConfigDict


class ApiError(BaseModel):
    Message: str | None = None


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    access_token: str
    token_type: str
    expires_in: int | None = None


class UserBookingData(BaseModel):
    model_config = ConfigDict(extra="allow")
    OrderId: int | str | None = None
    TicketsNumber: str | List[str] | None = None


class UserBookingGatewayResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    Response: str | None = None
    Data: UserBookingData | None = None


class UserBookingResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    PaymentUrl: str | None = None
    result: UserBookingGatewayResult | None = None

    @property
    def md_order(self) -> str | None:
        if not self.result or not self.result.Response:
            return None
        match = re.search(r"mdOrder=([a-zA-Z0-9-]+)", self.result.Response)
        return match.group(1) if match else None


class UserBookingResponse(BaseModel):
    Result: UserBookingResult | None = None
    Error: ApiError | None = None


class TicketItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    TicketNumber: str | None = None
    Id: int | None = None
    PdfUrl: str | None = None
    UserId: str | None = None
    Condition: str | None = None
    Passanger: str | None = None
    Price: float | None = None
    Currency: str | None = None
    DeteDeparture: str | None = None


class TicketsListResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    Collections: List[TicketItem] = []
    Count: int | None = None
    CurrentPage: int | None = None
    PageSize: int | None = None


class TicketsListResponse(BaseModel):
    Result: TicketsListResult | None = None
    Error: ApiError | None = None


class RoutePoint(BaseModel):
    model_config = ConfigDict(extra="allow")
    Name: str | None = None
    Latitude: str | None = None
    Longitude: str | None = None


class RouteDepartDetails(BaseModel):
    model_config = ConfigDict(extra="allow")
    DepartTime: str | None = None
    ArriveTime: str | None = None
    DepartureDateTime: str | None = None
    ArrivalDateTime: str | None = None
    DepartDate: str | None = None
    ArriveDate: str | None = None
    RouteDate: str | None = None
    DepartPoint: RoutePoint | None = None
    ArrivePoint: RoutePoint | None = None


class TicketDetailsResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    TicketNumber: str | None = None
    ClientName: str | None = None
    PhoneNumber: str | None = None
    PhoneNumberTwo: str | None = None
    Email: str | None = None
    DateDepart: str | None = None
    PriceTicket: float | None = None
    CurrencyName: str | None = None
    CurrencyId: int | None = None
    PdfUrl: str | None = None
    Id: int | None = None
    CityDepart: str | None = None
    CityArrive: str | None = None
    CityDepartId: int | None = None
    CityArriveId: int | None = None
    TarifId: int | None = None
    TarifName: str | None = None
    PlaceDepart: int | None = None
    PlaceReturn: int | None = None
    ClientCitizenship: str | None = None
    ClientPasport: str | None = None
    ClientDateOfBirthDay: str | None = None
    Condition: str | None = None
    RouteDepart: RouteDepartDetails | None = None
    HasAbilityChangeDate: bool | None = None
    HasAbilityAnnulationTicket: bool | None = None


class TicketDetailsResponse(BaseModel):
    Result: TicketDetailsResult | None = None
    Error: ApiError | None = None


class TicketExistsResponse(BaseModel):
    Result: bool | None = None
    Error: ApiError | None = None


class TicketBlanksResponse(BaseModel):
    Result: Any = None
    Error: ApiError | None = None
