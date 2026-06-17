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


class RouteDepartDetails(BaseModel):
    model_config = ConfigDict(extra="allow")
    DepartTime: str | None = None
    ArriveTime: str | None = None
    DepartureDateTime: str | None = None
    ArrivalDateTime: str | None = None


class TicketDetailsResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    TicketNumber: str | None = None
    ClientName: str | None = None
    PhoneNumber: str | None = None
    DateDepart: str | None = None
    PriceTicket: float | None = None
    CurrencyName: str | None = None
    PdfUrl: str | None = None
    Id: int | None = None
    RouteDepart: RouteDepartDetails | None = None
    HasAbilityChangeDate: bool | None = None
    HasAbilityAnnulationTicket: bool | None = None


class TicketDetailsResponse(BaseModel):
    Result: TicketDetailsResult | None = None
    Error: ApiError | None = None


class TicketBlanksResponse(BaseModel):
    Result: Any = None
    Error: ApiError | None = None
