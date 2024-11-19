from typing import Dict, List, Optional, Union

class Node(object):
    host: str
    port: Union[int, str]
    path: str
    protocol: str
    healthy: bool

    def __init__(self, url: str) -> None: ...  # type: ignore
    def __init__(  # noqa: F811
        self, host: str, port: Union[int, str], path: str, protocol: str
    ) -> None: ...
    def url(self) -> str: ...

class Configuration(object):
    nodes: List[Node]
    nearest_node: Optional[Node]
    api_key: str
    connection_timeout_seconds: float
    num_retries: int
    retry_interval_seconds: float
    healthcheck_interval_seconds: float
    verify: bool

    def __init__(
        self,
        config_dict: Dict[str, Union[str, List[Union[str, Dict[str, str]]], float, int, bool]],
    ) -> None: ...
    @staticmethod
    def validate_config_dict(
        config_dict: Dict[str, Union[str, List[Union[str, Dict[str, str]]], float, int, bool]],
    ) -> None: ...
    @staticmethod
    def validate_node_fields(node: Union[str, Dict[str, str]]) -> bool: ...
    @staticmethod
    def show_deprecation_warnings(
        config_dict: Dict[str, Union[str, List[Union[str, Dict[str, str]]], float, int, bool]],
    ) -> None: ...
