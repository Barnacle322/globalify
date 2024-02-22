from dataclasses import dataclass, field
from enum import Enum


class NotificationDestination(Enum):
    ALL = "all"
    SEARCH = "search"
    ONBOARDING = "onboarding"
    COMPANY = "change_company_info"
    VERIFICATION = "email_verification"
    INDEX = "index"
    EXPANDED_ONBOARDING = "expanded_onboarding"


class StatusType(Enum):
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


class Status:
    status_type: StatusType
    msg: str

    def __init__(self, type: StatusType = StatusType.ERROR, msg="An unknown error occurred."):
        self.status_type = type
        self.msg = msg

    def __repr__(self):
        return f"<{self.status_type} {self.msg}>"

    def get_status(self, **kwargs) -> dict[str, str]:
        return {"type": str(self.status_type.value), "msg": self.msg, **kwargs}


class OauthProvider(Enum):
    GOOGLE = "google"
    LINKEDIN = "linkedin"
    APPLE = "apple"


class Tier(Enum):
    FREE = "free"
    ELEVATE = "elevate"
    CONNECT = "connect pro"
    BOOST = "boost academy"


class Events(Enum):
    STRIPE_INVOICE_PAID = "stripe.invoice_paid"
    STRIPE_INVOICE_UPCOMING = "stripe.invoice_upcoming"
    STRIPE_TRIAL_WILL_END = "stripe.trial_will_end"
    STRIPE_PAYMENT_FAILED = "stripe.payment_failed"
    STRIPE_PAYMENT_SUCCEDED = "stripe.payment_succeeded"

    USER_COMPLETED_ONBOARDING = "user.completed_onboarding"


@dataclass
class ButtonLayout:
    text: str
    url: str
    dismiss: bool = True

    def get_json(self) -> dict[str, str]:
        return {"text": self.text, "url": self.url}


@dataclass
class NotificationLayout:
    title: str
    msg: str | None = None
    buttons: list[ButtonLayout] = field(default_factory=list)
    icon_url: str | None = None
    is_closable: bool = True

    def get_json(self, **kwargs) -> dict[str, str]:
        json_dict = {
            "title": self.title,
            **self.__dict__,
            **kwargs,
        }
        return json_dict
