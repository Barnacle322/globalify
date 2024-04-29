import json

from utils.typesense_helpers.typesense_search import (
    SearchBuilder,
)

industries = []

with open("signal_investors.jsonl", encoding="UTF-8") as file:
    data = file.readlines()

    for value in data:
        # print(value)
        # print(json.loads(value))
        name = (json.loads(value)).get("industry").split(",")

        industries += name

print(list(set(industries)))

for i in list(set(industries)):
    result = SearchBuilder("industries").query(i).query_by(["embedding"]).search()
    found = result.get("hits", [])
    industries = []
    for hit in result.get("hits", []):
        hit = hit.get("document", {})
        industries.append(
            {
                "id": hit.get("db_id", 0),
                "name": hit.get("name", ""),
            }
        )
    print(i, (industries[0] if industries else "Not found"), result.get("found", 0))
