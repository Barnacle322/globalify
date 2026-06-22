from enum import Enum

from ..utils.errors.error_messages import UNKNOWN_ERROR


class NotificationType(Enum):
    INFO = "info"
    WARNING = "warning"


class StatusType(Enum):
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


class Status:
    status_type: StatusType
    msg: str

    def __init__(self, type: StatusType = StatusType.ERROR, msg=UNKNOWN_ERROR):
        self.status_type = type
        self.msg = msg

    def __repr__(self):
        return f"<{self.status_type} {self.msg}>"

    def get_status(self, **kwargs) -> dict[str, str]:
        return {"type": str(self.status_type.value), "msg": self.msg, **kwargs}


class Tier(Enum):
    FREE = "free"
    PREMIUM_MONTHLY = "premium monthly"
    PREMIUM_YEARLY = "premium annual"


class Events(Enum):
    INVESTOR_PROFILE_CLAIM_REQUEST = "investor.profile_claim_request"


class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SearchHistoryType(Enum):
    INVESTOR = "investor"
    INVESTMENT_FIRM = "investment_firm"
    COMPANY = "company"
