import os

import typesense

client = typesense.Client(
    {
        "nodes": [
            {
                "host": os.getenv("_TYPESENSE_HOST", "localhost"),
                "port": os.getenv("_TYPESENSE_PORT", "8108"),
                "protocol": "http",
            }
        ],
        "api_key": os.getenv("_TYPESENSE_API_KEY", "xyz"),
        "connection_timeout_seconds": 2,
    }
)


def create_schema(schema: dict) -> None:
    if not schema:
        schema = {
            "name": "investors",
            "fields": [
                {"name": "name", "type": "string"},
                {
                    "name": "db_id",
                    "type": "int32",
                    "facet": True,
                },
                {"name": "firm_name", "type": "string", "optional": True},
                {"name": "about", "type": "string", "optional": True},
                {"name": "position", "type": "string", "facet": True, "optional": True},
                {"name": "n_investments", "type": "int32", "optional": True},
                {"name": "n_exits", "type": "int32", "optional": True},
                {"name": "min_investment", "type": "int32", "optional": True},
                {"name": "max_investment", "type": "int32", "optional": True},
                {"name": "location", "type": "string", "facet": True, "optional": True},
                {"name": "rounds", "type": "string[]", "facet": True, "optional": True},
                {"name": "industries", "type": "string[]", "facet": True, "optional": True},
                {"name": "notable_investments", "type": "string[]", "optional": True},
            ],
        }

    client.collections.create(schema)


def populate_schema(
    schema_name: str,
    file_name: str = "./investor_index.jsonl",
) -> None:
    with open(file_name, encoding="utf-8") as jsonl_file:
        client.collections[schema_name].documents.import_(  # type: ignore
            jsonl_file.read().encode("utf-8")
        )


def delete_schema(schema_name: str) -> None:
    client.collections[schema_name].delete()  # type: ignore


def search(collection: str, q: str, query_by: str, sort_by: str = "db_id:asc", per_page: int = 10, page: int = 1):
    search_parameters = {
        "q": q,
        "query_by": query_by,
        "per_page": per_page,
        "sort_by": sort_by,
        "page": page,
    }

    results = client.collections[collection].documents.search(search_parameters)  # type: ignore
    return results


# if __name__ == "__main__":
# delete_schema("investors")
# create_schema({})
# populate_schema("investors")
# searchh = search(
#     collection="investors",
#     q="Pre-seed web3",
#     query_by="name, firm_name, about, position, location, rounds, industries, notable_investments",
#     per_page=250,
#     page=1,
# )
# print(len(searchh))
# print(searchh)
