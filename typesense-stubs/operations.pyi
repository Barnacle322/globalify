from typing import Any, Dict, Optional

from .api_call import ApiCall

class Operations(object):
    RESOURCE_PATH: str
    HEALTH_PATH: str
    api_call: ApiCall

    def __init__(self, api_call: ApiCall) -> None: ...
    @staticmethod
    def _endpoint_path(operation_name: str) -> str: ...
    def perform(self, operation_name: str, query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: ...
    def is_healthy(self) -> bool: ...
