from typing import Any, Dict

from .documents import Documents
from .overrides import Overrides
from .synonyms import Synonyms

class Collection:
    name: str
    api_call: Any
    documents: Documents
    overrides: Overrides
    synonyms: Synonyms

    def __init__(self, api_call: Any, name: str) -> None: ...
    def _endpoint_path(self) -> str: ...
    def retrieve(self) -> dict[str, Any]: ...
    def update(self, schema_change: dict[str, Any]) -> dict[str, Any]: ...
    def delete(self, params: Dict[str, Any] | None = None) -> dict[str, Any]: ...
