from typing import Callable, Dict, List, Optional, Type, Union

from .configuration import Configuration, Node
from .exceptions import (
    HTTPStatus0Error,
    ObjectAlreadyExists,
    ObjectNotFound,
    ObjectUnprocessable,
    RequestForbidden,
    RequestMalformed,
    RequestUnauthorized,
    ServerError,
    ServiceUnavailable,
    TypesenseClientError,
)

class ApiCall(object):
    API_KEY_HEADER_NAME: str
    config: Configuration
    nodes: List[Node]
    node_index: int

    def __init__(self, config: Configuration) -> None: ...
    def _initialize_nodes(self) -> None: ...
    def node_due_for_health_check(self, node: Node) -> bool: ...
    def get_node(self) -> Node: ...
    @staticmethod
    def get_exception(
        http_code: int,
    ) -> Type[
        Union[
            HTTPStatus0Error,
            RequestMalformed,
            RequestUnauthorized,
            RequestForbidden,
            ObjectNotFound,
            ObjectAlreadyExists,
            ObjectUnprocessable,
            ServerError,
            ServiceUnavailable,
            TypesenseClientError,
        ]
    ]: ...
    def make_request(
        self,
        fn: Callable,
        endpoint: str,
        as_json: bool,
        **kwargs: Union[str, int, float, bool],
    ) -> Union[Dict[str, Union[str, int, float, bool]], str]: ...
    def set_node_healthcheck(self, node: Node, is_healthy: bool) -> None: ...
    @staticmethod
    def normalize_params(params: Dict[str, Union[str, int, float, bool]]) -> None: ...
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
        as_json: bool = True,
    ) -> Union[Dict[str, Union[str, int, float, bool]], str]: ...
    def post(
        self,
        endpoint: str,
        body: Union[str, Dict[str, Union[str, int, float, bool]]],
        params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
        as_json: bool = True,
    ) -> Union[Dict[str, Union[str, int, float, bool]], str]: ...
    def put(
        self,
        endpoint: str,
        body: Union[str, Dict[str, Union[str, int, float, bool]]],
        params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> Dict[str, Union[str, int, float, bool]]: ...
    def patch(
        self,
        endpoint: str,
        body: Union[str, Dict[str, Union[str, int, float, bool]]],
        params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> Dict[str, Union[str, int, float, bool]]: ...
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
    ) -> Dict[str, Union[str, int, float, bool]]: ...
