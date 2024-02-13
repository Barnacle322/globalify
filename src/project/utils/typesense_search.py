import os

from typesense.client import Client

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
        "connection_timeout_seconds": 100,
    }
)


class SearchBuilder:
    def __init__(self):
        self.parameters = {}
        self.filters = []

    def with_query(self, query: str):
        """
        Sets the query parameter.

        Args:
            query (str): The search query.
        """
        self.parameters["q"] = query
        return self

    def with_query_by(self, fields: list[str], weights: list[int] | None = None):
        """
        Sets the query_by and query_by_weights parameters.

        Args:
            fields (list[str]): The fields to query by.
            weights (list[int] | None): The weights for the fields.

        Raises:
            ValueError: If fields and weights have different lengths.
        """
        if weights is not None and len(fields) != len(weights):
            raise ValueError("fields and weights must have the same length")
        self.parameters["query_by"] = ",".join(fields)
        if weights is not None:
            self.parameters["query_by_weights"] = ",".join(str(weight) for weight in weights)
        return self

    def with_filter_by_rounds(self, rounds: list[str] | None, exclusivity: bool = True):
        if rounds:
            if exclusivity:
                for round in rounds:
                    self.filters.append(f"rounds:={round}")
            else:
                self.filters.append(f'rounds:=[{",".join(rounds)}]')
        return self

    def with_filter_by_industries(self, industries: list[str] | None, exclusivity: bool = True):
        if industries:
            if exclusivity:
                for industry in industries:
                    self.filters.append(f"industries:={industry}")
            else:
                self.filters.append(f'industries:=[{",".join(industries)}]')
        return self

    def with_filter_by_investment_range(self, min_investment: int | None, max_investment: int | None):
        if min_investment:
            self.filters.append(f"min_investment:>{min_investment}")
        if max_investment:
            self.filters.append(f"max_investment:<{max_investment}")
        return self

    # def with_filter_by_rounds(self, rounds: list[str], rounds_exclusive: bool | None = False):
    #     if rounds_exclusive and len(rounds) > 1:
    #         conditions = []
    #         for round in rounds:
    #             conditions.append(f"rounds: {round}")
    #         self.parameters["filter_by"] = " && ".join(conditions)
    #     elif len(rounds) > 1:
    #         self.parameters["filter_by"] = f"rounds: [{", ".join(rounds)}]"
    #     else:
    #         self.parameters["filter_by"] = f"rounds: {rounds[0]}"

    #     return self

    # def with_filter_by_industries(self, industries: list[str], industries_exclusive: bool | None = False):
    #     if industries:
    #         if self.parameters["filter_by"] is None:
    #             if industries_exclusive and len(industries) > 1:
    #                 conditions = []
    #                 for industry in industries:
    #                     conditions.append(f"industries: {industry}")
    #                 self.parameters["filter_by"] = " && ".join(conditions)
    #             elif len(industries) > 1:
    #                 self.parameters["filter_by"] = f"industries: [{", ".join(industries)}]"
    #             else:
    #                 self.parameters["filter_by"] = f"industries: {industries[0]}"
    #         else:
    #             if industries_exclusive and len(industries) > 1:
    #                 conditions = []
    #                 for industry in industries:
    #                     conditions.append(f"industries: {industry}")
    #                 self.parameters["filter_by"] += " && " + " && ".join(conditions)
    #             elif len(industries) > 1:
    #                 self.parameters["filter_by"] += " && " + f"industries: [{", ".join(industries)}]"
    #             else:
    #                 self.parameters["filter_by"] += " && " + f"industries: {industries[0]}"
    #     return self

    # def with_filter_by_investment_range(self, min_investment: int | None, max_investment: int | None):
    # if self.parameters["filter_by"] is None:
    # if min_investment and max_investment:
    #     self.parameters["filter_by"] = f"min_investment:<={max_investment} && max_investment:>={min_investment} && "
    # elif min_investment is not None:
    #     self.parameters["filter_by"] = f"max_investment:>={min_investment} && "
    # elif max_investment is not None:
    #     self.parameters["filter_by"] = f"min_investment:<={max_investment} && "
    # else:
    #     if min_investment and max_investment:
    #         self.parameters["filter_by"] += (
    #             " && " + f"min_investment:<={max_investment} && max_investment:>={min_investment}"
    #         )
    #     elif min_investment is not None:
    #         self.parameters["filter_by"] += " && " + f"max_investment:>={min_investment}"
    #     elif max_investment is not None:
    #         self.parameters["filter_by"] += " && " + f"min_investment:<={max_investment}"

    # return self

    # def with_filter_by_countries(self, countries: list[str]):
    #     if len(countries) > 1:
    #         self.parameters["filter_by"] = f"countries: [{", ".join(countries)}]"
    #     else:
    #         self.parameters["filter_by"] = f"countries: {countries[0]}"

    #     return self

    def with_sort(self, sort_by: str | None, sort_desc: bool | None):
        """
        Sets the sort_by parameter.

        Args:
            sorts (List[Tuple[str, str]]): The fields to sort by and their directions.

        Returns:
            SearchBuilder: The builder instance.

        Raises:
            ValueError: If more than 3 fields are provided.
        """
        if sort_by:
            if sort_desc:
                self.parameters["sort_by"] = f"{sort_by}:desc"
            else:
                self.parameters["sort_by"] = f"{sort_by}:asc"
        else:
            return self
        return self

    def with_pinned_hits(self, hits: list[tuple[str, int]]):
        """
        Sets the pinned_hits parameter.

        Args:
            hits (list[tuple[str, int]]): The records to pin and their positions.

        Returns:
            SearchBuilder: The builder instance.
        """
        self.parameters["pinned_hits"] = ",".join(f"{record_id}:{position}" for record_id, position in hits)
        return self

    def with_hidden_hits(self, hits: list[str]):
        """
        Sets the hidden_hits parameter.

        Args:
            hits (list[str]): The records to hide.

        Returns:
            SearchBuilder: The builder instance.
        """
        self.parameters["hidden_hits"] = ",".join(hits)
        return self

    def with_group_by(self, fields: list[str]):
        """
        Sets the group_by parameter.

        Args:
            fields (list[str]): The fields to group by.

        Returns:
            SearchBuilder: The builder instance.
        """
        self.parameters["group_by"] = ",".join(fields)
        return self

    def with_page(self, page: int):
        """
        Sets the page parameter.

        Args:
            page (int): The page number.
        """
        self.parameters["page"] = page
        return self

    def with_per_page(self, per_page: int):
        """
        Sets the per_page parameter.

        Args:
            per_page (int): The number of results per page.
        """
        self.parameters["per_page"] = per_page
        return self

    def build(self) -> dict:
        self.parameters["prefix"] = False
        self.parameters["filter_by"] = " && ".join(self.filters)
        return self.parameters


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


def upsert_documents(schema_name: str, data: list[dict]):
    if schema_name and data:
        print(f"Populating {schema_name} schema")
        client.collections[schema_name].documents.import_(
            data,
            {
                "action": "upsert",
                "filter_by": "db_id",
            },
        )
        print(f"Populated {schema_name} schema")
        return client.collections[schema_name].documents.export({"include_fields": "id, db_id"})
    else:
        raise ValueError("Schema name and file path are required")


def delete_schema(schema_name: str) -> None:
    if schema_name:
        print(f"Deleting {schema_name} schema")
        client.collections[schema_name].delete()
        print(f"Deleted {schema_name} schema")
    else:
        raise ValueError("Schema name is required")


def setup():
    investor_schema = {
        "name": "investors",
        "fields": [
            {"name": "name", "type": "string", "sort": True},
            {
                "name": "db_id",
                "type": "int32",
                "facet": True,
            },
            {"name": "firm_name", "type": "string", "optional": True, "sort": True},
            {"name": "about", "type": "string", "optional": True},
            {"name": "position", "type": "string", "facet": True, "optional": True, "sort": True},
            {"name": "n_investments", "type": "int32", "optional": True, "sort": True},
            {"name": "n_exits", "type": "int32", "optional": True, "sort": True},
            {"name": "min_investment", "type": "int32", "optional": True, "sort": True},
            {"name": "max_investment", "type": "int32", "optional": True, "sort": True},
            {"name": "location", "type": "string", "facet": True, "optional": True, "sort": True},
            {"name": "rounds", "type": "string[]", "facet": True, "optional": True},
            {"name": "industries", "type": "string[]", "facet": True, "optional": True},
            {"name": "notable_investments", "type": "string[]", "optional": True},
            {
                "name": "embedding",
                "type": "float[]",
                "embed": {
                    "from": [
                        "name",
                        "firm_name",
                        "about",
                        "position",
                        "location",
                        "rounds",
                        "industries",
                        "notable_investments",
                    ],
                    "model_config": {
                        "model_name": "ts/all-MiniLM-L12-v2",
                    },
                },
            },
        ],
        "primary_key": "db_id",
    }

    try:
        delete_schema("investors")
    except Exception as e:
        print(f"Error deleting investors schema: {e}")
    create_schema(investor_schema)
    # populate_schema_from_file("investors", file_path="./investor_index.jsonl")

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
    populate_schema_from_file("cities", file_path="./cities_index.jsonl")


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
    filter_by: str | None = None,
    sort_by: str | None = None,
    per_page: int = 12,
    page: int = 1,
):
    search_parameters = {
        "q": q,
        "query_by": query_by,
        "filter_by": filter_by,
        "sort_by": sort_by,
        "per_page": per_page,
        "page": page,
        "prefix": False,
    }
    print(search_parameters)

    results = client.collections[collection].documents.search(search_parameters)
    return results


def create_index(file_name: str):
    import csv
    import json

    with open(file_name, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            with open("cities_index.jsonl", "a", encoding="utf-8") as jsonl_file:
                json_row = {}
                json_row["city"] = row["city"]
                json_row["city_ascii"] = row["city_ascii"]
                json_row["country"] = row["country"]
                json_row["admin_name"] = row["admin_name"]
                json_row["population"] = int(float(row.get("population", 0))) if row.get("population") != "" else 0
                json_row["latitude"] = float(row["lat"])
                json_row["longitude"] = float(row["lng"])
                jsonl_file.write(json.dumps(json_row) + "\n")


# params = {
#     "q": "singapore",
#     "query_by": "location,rounds,industries,embedding,notable_investments,name,firm_name,position",
#     "filter_by": "rounds: Seed && rounds: Pre-Seed || industries: FinTech",
#     "sort_by": "",
#     "per_page": 10,
#     "page": 1,
#     "prefix": False,
# }
# print(client.collections["investors"].documents.search(params))
