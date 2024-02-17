import click

from .typesense_search import setup as typesense_setup


@click.group()
def cli():
    pass


@cli.command()
def setup():
    typesense_setup()


if __name__ == "__main__":
    cli()
