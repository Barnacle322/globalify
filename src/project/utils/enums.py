from enum import Enum, StrEnum

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


# ---------------------------------------------------------------------------
# Phase 1b — Entity model enums
# ---------------------------------------------------------------------------


class EntityType(StrEnum):
    PERSON = "person"
    ORG = "org"


class OrgType(StrEnum):
    VC_FIRM = "vc_firm"
    MICRO_VC = "micro_vc"
    ANGEL_GROUP = "angel_group"
    CORPORATE_VC = "corporate_vc"
    FAMILY_OFFICE = "family_office"
    ACCELERATOR = "accelerator"
    INCUBATOR = "incubator"
    VENTURE_STUDIO = "venture_studio"
    PE_FIRM = "pe_firm"
    GROWTH_EQUITY = "growth_equity"
    SYNDICATE = "syndicate"
    LP_FUND_OF_FUNDS = "lp_fund_of_funds"
    GRANT_PROGRAM = "grant_program"
    GOVERNMENT_PROGRAM = "government_program"
    VENTURE_DEBT = "venture_debt"
    CROWDFUNDING_PLATFORM = "crowdfunding_platform"
    SEARCH_FUND = "search_fund"
    HEDGE_FUND = "hedge_fund"
    OTHER = "other"


class PersonType(StrEnum):
    ANGEL = "angel"
    PARTNER = "partner"
    OPERATOR = "operator"
    SCOUT = "scout"
    LP = "lp"


class AffiliationRole(StrEnum):
    FOUNDER = "founder"
    GP = "gp"
    PARTNER = "partner"
    PRINCIPAL = "principal"
    ASSOCIATE = "associate"
    SCOUT = "scout"
    ADVISOR = "advisor"
    LP = "lp"
    OPERATOR = "operator"


class InvestorType(StrEnum):
    ANGEL = "angel"
    ANGEL_SYNDICATE = "angel_syndicate"
    ANGEL_GROUP = "angel_group"
    SCOUT = "scout"
    MICRO_VC = "micro_vc"
    VC_FIRM = "vc_firm"
    GROWTH_EQUITY = "growth_equity"
    CORPORATE_VC = "corporate_vc"
    ACCELERATOR = "accelerator"
    INCUBATOR = "incubator"
    VENTURE_STUDIO = "venture_studio"
    FAMILY_OFFICE = "family_office"
    PRIVATE_EQUITY = "private_equity"
    VENTURE_DEBT = "venture_debt"
    CROWDFUNDING_PLATFORM = "crowdfunding_platform"
    GRANT_PROGRAM = "grant_program"
    GOVERNMENT_PROGRAM = "government_program"
    SEARCH_FUND = "search_fund"
    FUND_OF_FUNDS = "fund_of_funds"
    LIMITED_PARTNER = "limited_partner"
    HEDGE_FUND = "hedge_fund"
    OTHER = "other"


class InvestmentStage(StrEnum):
    IDEA = "idea"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D_PLUS = "series_d_plus"
    GROWTH = "growth"
    LATE_STAGE = "late_stage"
    DEBT = "debt"
    SECONDARY = "secondary"


class LeadPreference(StrEnum):
    LEAD = "lead"
    FOLLOW = "follow"
    BOTH = "both"
    UNKNOWN = "unknown"
