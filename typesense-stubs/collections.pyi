from typing import Any, Dict

from .api_call import ApiCall
from .collection import Collection

class Collections(object):
    RESOURCE_PATH: str
    api_call: ApiCall
    collections: Dict[str, Collection]

    def __init__(self, api_call: ApiCall) -> None: ...
    def __getitem__(self, collection_name: str) -> Collection: ...
    def create(self, schema: Dict[str, Any]) -> Dict[str, Any]: ...
    def retrieve(self) -> Dict[str, Any]: ...
