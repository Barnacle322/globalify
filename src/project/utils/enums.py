from dataclasses import dataclass, field
from enum import Enum


class NotificationDestination(Enum):
    ALL = "all"
    SEARCH = "search"
    ONBOARDING = "onboarding"
    COMPANY = "change_company_info"
    VERIFICATION = "email_verification"
    INDEX = "index"


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
    PREMIUM_MONTHLY = "premium monthly"
    PREMIUM_YEARLY = "premium annual"


class Events(Enum):
    STRIPE_INVOICE_PAID = "stripe.invoice_paid"
    STRIPE_INVOICE_UPCOMING = "stripe.invoice_upcoming"
    STRIPE_TRIAL_WILL_END = "stripe.trial_will_end"
    STRIPE_PAYMENT_FAILED = "stripe.payment_failed"
    STRIPE_PAYMENT_SUCCEDED = "stripe.payment_succeeded"

    USER_COMPLETED_ONBOARDING = "user.completed_onboarding"


class CompanyRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EMPLOYEE = "employee"


@dataclass
class ButtonLayout:
    text: str
    url: str
    dismiss: bool = True

    def get_json(self) -> dict[str, str | bool]:
        return {"text": self.text, "url": self.url, "dismiss": self.dismiss}


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
            "is_closable": self.is_closable,
            **kwargs,
        }

        if self.msg:
            json_dict["msg"] = self.msg
        if self.buttons and self.buttons != []:
            json_dict["buttons"] = [button.get_json() for button in self.buttons]
        if self.icon_url:
            json_dict["icon_url"] = self.icon_url

        return json_dict


class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
