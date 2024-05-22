from pydantic import BaseModel


class InvestorBookmarkSchema(BaseModel):
    id: int
    name: str
    position: str
    firm_name: str
