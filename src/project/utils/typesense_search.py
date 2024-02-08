import os

from typesense.client import Client

client = Client(
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
    if schema:
        client.collections.create(schema)
    else:
        raise ValueError("Schema is required")


def populate_schema(
    schema_name: str,
    file_path: str = "./investor_index.jsonl",
) -> None:
    if schema_name and file_path:
        with open(file_path, encoding="utf-8") as jsonl_file:
            client.collections[schema_name].documents.import_(jsonl_file.read().encode("utf-8"), {"action": "upsert"})
    else:
        raise ValueError("Schema name and file path are required")


def delete_schema(schema_name: str) -> None:
    if schema_name:
        client.collections[schema_name].delete()
    else:
        raise ValueError("Schema name is required")


def setup():
    investor_schema = {
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
        delete_schema("investors")
    except Exception as e:
        print(f"Error deleting investors schema: {e}")
    create_schema(investor_schema)
    populate_schema("investors", file_path="./investor_index.jsonl")

    try:
        delete_schema("cities")
    except Exception as e:
        print(f"Error deleting cities schema: {e}")
    create_schema(city_schema)
    populate_schema("cities", file_path="./cities_index.jsonl")


def update_schema(schema_name: str, file_path: str) -> None:
    if schema_name and file_path:
        with open(file_path, encoding="utf-8") as jsonl_file:
            smth = client.collections[schema_name]
            if smth:
                smth.documents.import_(jsonl_file.read().encode("utf-8"), params={"action": "upsert"})
    else:
        raise ValueError("Schema name and file path are required")


def search(collection: str, q: str, query_by: str, sort_by: str | None = None, per_page: int = 10, page: int = 1):
    if not sort_by:
        search_parameters = {
            "q": q,
            "query_by": query_by,
            "per_page": per_page,
            "page": page,
        }
    else:
        search_parameters = {
            "q": q,
            "query_by": query_by,
            "sort_by": sort_by,
            "per_page": per_page,
            "page": page,
        }

    results = client.collections[collection].documents.search(search_parameters)
    return results


# if __name__ == "__main__":
# searchh = search(
#     collection="investors",
#     q="Pre-seed web3",
#     query_by="name, firm_name, about, position, location, rounds, industries, notable_investments",
#     per_page=250,
#     page=1,
# )
# print(len(searchh))
# print(searchh)

# if __name__ == "__main__":
#     searchh = search(
#         collection="cities",
#         q="Osh",
#         query_by="city, city_ascii, country, admin_name",
#         per_page=10,
#         page=1,
#     )

#     print(len(searchh))
#     print(searchh)

#     for result in searchh["hits"]:
#         print(
#             result.get("document").get("city"),
#             result.get("document").get("admin_name"),
#             result.get("document").get("country"),
#             result.get("document").get("population"),
#             result.get("document").get("latitude"),
#             result.get("document").get("longitude"),
#             sep=" | ",
#         )


# def create_index(file_name: str):
#     # CSV reader
#     import csv
#     import json

#     with open(file_name, newline="", encoding="utf-8") as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             with open("cities_index.jsonl", "a", encoding="utf-8") as jsonl_file:
#                 json_row = {}
#                 json_row["city"] = row["city"]
#                 json_row["city_ascii"] = row["city_ascii"]
#                 json_row["country"] = row["country"]
#                 json_row["admin_name"] = row["admin_name"]
#                 json_row["population"] = int(float(row.get("population", 0))) if row.get("population") != "" else 0
#                 json_row["latitude"] = float(row["lat"])
#                 json_row["longitude"] = float(row["lng"])
#                 jsonl_file.write(json.dumps(json_row) + "\n")


# if __name__ == "__main__":
#     create_local()
