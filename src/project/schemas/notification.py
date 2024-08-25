from pydantic import BaseModel


class NotificationItem(BaseModel):
    type: str | None
    url: str | None = None


class NotificationLayout(BaseModel):
    title: str
    msg: str | None = None
    type: str | None = None
    item: NotificationItem | None = None
