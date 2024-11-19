import os
from typing import Any

from typesense.client import Client
from typesense.exceptions import ObjectNotFound

from ..info_lists import synonyms

client = Client(
    {
        "nodes": [
            {
                "host": os.getenv("_TYPESENSE_HOST", "127.0.0.1"),
                "port": os.getenv("_TYPESENSE_PORT", "8108"),
                "protocol": "http",
            }
        ],
        "api_key": os.getenv("_TYPESENSE_API_KEY", "xyz"),
        "connection_timeout_seconds": 1000,
    }
)


class SearchBuilder:
    def __init__(self, collection: str):
        self.collection = collection
        self.parameters = {}
        self.filters = []

    def query(self, query: str):
        self.parameters["q"] = query if query else "*"
        return self

    def query_by(self, fields: list[str], weights: list[int] | None = None):
        if weights is not None and len(fields) != len(weights):
            raise ValueError("fields and weights must have the same length")
        self.parameters["query_by"] = ",".join(fields)
        if weights is not None:
            self.parameters["query_by_weights"] = ",".join(str(weight) for weight in weights)
        return self

    def filter_by(self, field: str, values: list[str] | None, exclusivity: bool = True):
        if not values:
            return self

        if exclusivity:
            for value in values:
                self.filters.append(f"{field}:={value}")
        else:
            self.filters.append(f'{field}:=[{",".join(values)}]')
        return self

    def filter_by_investment_range(self, min_investment: int | None, max_investment: int | None):
        if min_investment and max_investment:
            self.filters.append(f"min_investment:<={max_investment} && max_investment:>={min_investment}")
        elif min_investment is not None:
            self.filters.append(f"max_investment:>={min_investment}")
        elif max_investment is not None:
            self.filters.append(f"min_investment:<={max_investment}")
        return self

    def filter_by_boolean(self, field: str, value: bool):
        if field in ["is_public", "is_approved"]:
            self.filters.append(f"{field}:{str(value).lower()}")
        return self

    def sort_by(self, sort_by: str | None, sort_desc: bool | None):
        if sort_by:
            if sort_desc:
                self.parameters["sort_by"] = f"{sort_by}:desc"
            else:
                self.parameters["sort_by"] = f"{sort_by}:asc"

        return self

    def pinned_hits(self, hits: list[tuple[str, int]]):
        self.parameters["pinned_hits"] = ",".join(f"{record_id}:{position}" for record_id, position in hits)
        return self

    def hidden_hits(self, hits: list[str]):
        self.parameters["hidden_hits"] = ",".join(hits)
        return self

    def group_by(self, fields: list[str]):
        self.parameters["group_by"] = ",".join(fields)
        return self

    def page(self, page: int, per_page: int):
        self.parameters["page"] = page
        self.parameters["per_page"] = per_page
        return self

    def search(self) -> dict:
        if os.getenv("FLASK_ENV") == "testing":
            return {"found": 0, "page": 1, "per_page": 9, "hits": []}
        self.parameters["prefix"] = False

        # IMPORTANT: Control the weight of the embedding field in the search with the distance_threshold parameter
        if "embedding" in self.parameters["query_by"]:
            self.parameters["vector_query"] = "embedding:([], distance_threshold:0.50)"
            self.parameters["exclude_fields"] = "embedding"
        if self.filters:
            self.parameters["filter_by"] = " && ".join(self.filters)

        return client.collections[self.collection].documents.search(self.parameters)


def create_schema(schema: dict) -> None:
    if schema:
        print(f"Creating {schema['name']} schema")
        client.collections.create(schema)
        print(f"Created {schema['name']} schema")
    else:
        raise ValueError("Schema is required")


def populate_schema_from_file(
    schema_name: str,
    file_path: str = "./investor_index.jsonl",
) -> None:
    if schema_name and file_path:
        with open(file_path, encoding="utf-8") as jsonl_file:
            print(f"Populating {schema_name} schema")
            client.collections[schema_name].documents.import_(
                jsonl_file.read().encode("utf-8"),
                {
                    "action": "upsert",
                    "filter_by": "db_id",
                },
            )
            client.collections[schema_name].documents.export({"include_fields": "id, db_id"})
            print(f"Populated {schema_name} schema")
    else:
        raise ValueError("Schema name and file path are required")


def upsert_documents(schema_name: str, data: list[dict]) -> list[dict[str, Any]]:
    if schema_name and data:
        print(f"Populating {schema_name} schema")
        import_return = client.collections[schema_name].documents.import_(
            data,
            {"action": "upsert", "filter_by": "db_id", "return_id": "true"},
        )
        print(f"Populated {schema_name} schema")
        return import_return
    else:
        raise ValueError("Schema name and file path are required")


def update_collection(schema_name: str, update_schema: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if schema_name and update_schema:
        update_return = client.collections[schema_name].update(update_schema)
        print(f"Updated {schema_name} schema")
        return update_return
    else:
        raise ValueError("Schema name and update schema are required")


def delete_documents(schema_name: str, document_id: str) -> None:
    if schema_name and document_id:
        print(f"Deleting document from {schema_name} schema")
        try:
            client.collections[schema_name].documents.delete({"filter_by": f"db_id:={document_id}"})
            print(f"Deleted document from {schema_name} schema")
        except ObjectNotFound:
            print(f"Document with id {document_id} not found in {schema_name} schema")
    else:
        raise ValueError("Schema name and document id are required")


def delete_schema(schema_name: str) -> None:
    if schema_name:
        print(f"Deleting {schema_name} schema")
        client.collections[schema_name].delete()
        print(f"Deleted {schema_name} schema")
    else:
        raise ValueError("Schema name is required")


def setup():
    city_schema = {
        "name": "cities",
        "fields": [
            {"name": "city", "type": "string"},
            {"name": "city_ascii", "type": "string"},
            {"name": "country", "type": "string", "facet": True},
            {"name": "admin_name", "type": "string", "facet": True},
            {"name": "population", "type": "int32", "facet": True},
            {"name": "latitude", "type": "float", "facet": True},
            {"name": "longitude", "type": "float", "facet": True},
        ],
    }

    try:
        delete_schema("cities")
    except Exception as e:
        print(f"Error deleting cities schema: {e}")
    create_schema(city_schema)
    populate_schema_from_file("cities", file_path="./data/cities_index.jsonl")


def update_schema(schema_name: str, file_path: str) -> None:
    if schema_name and file_path:
        with open(file_path, encoding="utf-8") as jsonl_file:
            smth = client.collections[schema_name]
            if smth:
                smth.documents.import_(jsonl_file.read().encode("utf-8"), params={"action": "upsert"})
    else:
        raise ValueError("Schema name and file path are required")


def search(
    collection: str,
    q: str,
    query_by: str,
    per_page: int = 1,
    page: int = 1,
):
    search_parameters = {
        "q": q,
        "query_by": query_by,
        "per_page": per_page,
        "page": page,
        "prefix": False,
    }

    results = client.collections[collection].documents.search(search_parameters)
    return results


def create_synonyms(schema_name: str) -> None:
    for synonym in synonyms:
        print("Adding synonyms for", synonym["name"])
        client.collections[schema_name].synonyms.upsert(synonym["name"], synonym["item"])
