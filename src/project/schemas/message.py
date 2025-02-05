from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageSchema(BaseModel):
    id: int
    chat_id: int
    message: str
    type: str
    created: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSchema(BaseModel):
    id: int
    user_id: int
    created: datetime
    messages: list[MessageSchema] | None

    model_config = ConfigDict(from_attributes=True)


class ChatListSchema(BaseModel):
    id: int
    name: str
    user_id: int
    created: datetime

    model_config = ConfigDict(from_attributes=True)
