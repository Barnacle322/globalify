from typing import Any

from .aliases import Aliases
from .analytics import Analytics
from .api_call import ApiCall
from .collections import Collections
from .configuration import Configuration
from .debug import Debug
from .keys import Keys
from .multi_search import MultiSearch
from .operations import Operations

class Client:
    config: Configuration
    api_call: ApiCall
    collections: Collections
    multi_search: MultiSearch
    keys: Keys
    aliases: Aliases
    analytics: Analytics
    operations: Operations
    debug: Debug

    def __init__(self, config_dict: dict[str, Any]) -> None: ...
