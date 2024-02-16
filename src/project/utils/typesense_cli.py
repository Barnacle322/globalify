import click

from .typesense_search import delete_schema as typesense_delete_schema
from .typesense_search import populate_schema_from_file as typesense_populate_schema
from .typesense_search import search as typesense_search
from .typesense_search import setup as typesense_setup
from .typesense_search import update_schema as typesense_update_schema


@click.group()
def cli():
    pass


@cli.command()
@click.option("--schema_name", type=str)
@click.option("--file_path", type=str, default="./investor_index.jsonl")
def populate_schema(schema_name, file_path):
    typesense_populate_schema(schema_name, file_path)


@cli.command()
@click.option("--schema_name", type=str)
def delete_schema(schema_name):
    typesense_delete_schema(schema_name)


@cli.command()
def setup():
    typesense_setup()


@cli.command("update-schema")
@click.option("--schema_name", type=str)
@click.option("--file_path", type=str)
def update_schema(schema_name, file_path):
    typesense_update_schema(schema_name, file_path)


@cli.command("search-investors")
@click.option("--q", type=str, default="*")
@click.option(
    "--query_by",
    type=str,
    default="location, rounds, industries, embedding, notable_investments, name, firm_name, position",
)
@click.option("--per_page", type=int, default=10)
@click.option("--page", type=int, default=1)
def search(q, query_by, per_page, page):
    result = typesense_search("investors", q, query_by, per_page, page)
    for hit in result["hits"]:
        print(hit.get("document", {}).get("name"))


@cli.command("search-cities")
@click.option("--q", type=str, default="*")
@click.option("--query_by", type=str, default="city, city_ascii, country, admin_name")
@click.option("--per_page", type=int, default=10)
@click.option("--page", type=int, default=1)
def search_cities(q, query_by, per_page, page):
    result = typesense_search("cities", q, query_by, per_page, page)
    for hit in result["hits"]:
        print(hit.get("document", {}).get("city"))


if __name__ == "__main__":
    cli()
