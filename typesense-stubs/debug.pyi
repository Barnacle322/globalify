from typing import Any, Dict

from .api_call import ApiCall

class Debug(object):
    RESOURCE_PATH: str
    api_call: ApiCall
    collections: Dict[str, Any]

    def __init__(self, api_call: ApiCall) -> None: ...
    def retrieve(self) -> Dict[str, Any]: ...
