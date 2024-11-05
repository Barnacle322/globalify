from pydantic import BaseModel

class CompanyBookmarkSchema(BaseModel):
    id: int
    name: str