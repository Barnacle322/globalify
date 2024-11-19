from typing import Any, Dict

from .api_call import ApiCall

class MultiSearch(object):
    RESOURCE_PATH: str
    api_call: ApiCall

    def __init__(self, api_call: ApiCall) -> None: ...
    def perform(self, search_queries: Dict[str, Any], common_params: Dict[str, Any]) -> Dict[str, Any]: ...
