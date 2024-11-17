from .analytics_rules import AnalyticsRules
from .api_call import ApiCall

class Analytics(object):
    rules: AnalyticsRules

    def __init__(self, api_call: ApiCall) -> None: ...
