from enum import Enum


class StatusType(Enum):
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


class Status:
    type: StatusType
    msg: str

    def __init__(
        self, type: StatusType = StatusType.ERROR, msg="An unknown error occurred."
    ):
        self.type = type
        self.msg = msg

    def __repr__(self):
        return f"<{self.type} {self.msg}>"

    def get_status(self, **kwargs) -> dict[str, str]:
        return {"type": str(self.type.value), "msg": self.msg, **kwargs}


class OauthProvider(Enum):
    GOOGLE = "google"
    LINKEDIN = "linkedin"
