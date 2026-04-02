from pydantic import BaseModel


class TicketModel(BaseModel):
    ticket_id: str
    title: str
    status: str
    priority_raw: str
