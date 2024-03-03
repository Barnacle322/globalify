import csv
import json
from itertools import islice

import click
from population import get_industries, get_min_max_investment, get_notable_investments, get_rounds

from src.project.models.investor import Investor

from ...extensions import db

# class Config:
#     def __init__(self):
#         pass


# pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("file", type=click.File("r"), required=True)
@click.option(
    "--delimiter",
    default=";",
    prompt="Enter a delimiter for the file",
    help="Delimiter for the file",
    show_default=True,
)
def get_indices(file, delimiter):
    """Show indices for every attribute in csv file"""
    reader = csv.reader(file, delimiter=delimiter)
    headers = next(reader)
    for index, header in enumerate(headers):
        click.echo(f"<{header}> column has index <{index}>")


@cli.command()
@click.argument("file", type=click.File("r"), required=True)
@click.option(
    "--delimiter",
    default=";",
    prompt="Enter a delimiter for the file",
    help="Delimiter for the file",
    show_default=True,
)
@click.option(
    "--start-row",
    prompt="Enter a first row with data in the file",
    help="First row of the file",
    default=1,
    show_default=True,
    type=int,
)
@click.option(
    "--column-name",
    prompt="Enter a column number of full name. If first name and last name are in separated columns, enter numbers with a space between them ' '",
    help="Column for name",
)
@click.option(
    "--column-firm-name",
    prompt="Enter a column number of the firm name",
    help="Column for firm name",
    default="",
)
@click.option(
    "--column-position",
    prompt="Enter a column number of the position",
    help="Column for position",
    default="",
)
@click.option(
    "--column-about",
    prompt="Enter a column number of the about",
    help="Column for about",
    default="",
)
@click.option(
    "--column-email",
    prompt="Enter a column number of the email",
    help="Column for email",
    default="",
)
@click.option(
    "--column-linkedin",
    prompt="Enter a column number of the linkedin",
    help="Column for linkedin",
    default="",
)
@click.option(
    "--column-twitter",
    prompt="Enter a column number of the twitter",
    help="Column for twitter",
    default="",
)
@click.option(
    "--column-industry",
    prompt="Enter a column number of the industry",
    help="Column for industry",
    default="",
)
@click.option(
    "--column-rounds",
    prompt="Enter a column number of the rounds",
    help="Column for rounds",
    default="",
)
@click.option(
    "--column-investment-range",
    prompt="Enter a column number of the investment range or column numbers of minimum and maximum investment sums separated by a space ' '",
    help="Column for investment range",
    default="",
)
@click.option(
    "--column-location",
    prompt="Enter a column number of the location",
    help="Column for location",
    default="",
)
@click.option(
    "--column-notable-investments",
    prompt="Enter a column number of the notable investments",
    help="Column for notable investments",
    default="",
)
def set_columns(
    file,
    delimiter,
    start_row,
    column_name,
    column_firm_name,
    column_position,
    column_about,
    column_email,
    column_linkedin,
    column_twitter,
    column_industry,
    column_rounds,
    column_investment_range,
    column_location,
    column_notable_investments,
):
    """Set the attributes for our database from the csv file"""
    investor_list = []

    reader = csv.reader(file, delimiter=delimiter)
    for row in islice(reader, start_row, 3):
        """This function will be used to set the columns for the csv file and return the list of investors."""
        if len(column_name.split()) > 1:
            first_name = row[int(column_name.split(" ")[0])]
            last_name = row[int(column_name.split(" ")[1])]
        else:
            first_name = row[int(column_name)].split(" ")[0]
            last_name = row[int(column_name)].split(" ")[1] if len(row[int(column_name)].split(" ")) > 1 else None
        firm_name = row[int(column_firm_name)] if column_firm_name else None
        position = row[int(column_position)] if column_position else None
        about = row[int(column_about)] if column_about else None
        email = row[int(column_email)] if column_email else None
        linkedin = row[int(column_linkedin)] if column_linkedin else None
        twitter = row[int(column_twitter)] if column_twitter else None
        industry = row[int(column_industry)] if column_industry else None
        rounds = row[int(column_rounds)] if column_rounds else None
        if column_investment_range and len(column_investment_range.split()) > 1:
            investment_range = (
                row[int(column_investment_range.split(" ")[0])] + "-" + row[int(column_investment_range.split(" ")[1])]
            )
        elif column_investment_range:
            investment_range = row[int(column_investment_range)]
        else:
            investment_range = None
        location = row[int(column_location)] if column_location else None
        notable_investments = row[int(column_notable_investments)] if column_notable_investments else None

        investor = {
            "first_name": first_name,
            "last_name": last_name,
            "firm_name": firm_name,
            "position": position,
            "about": about,
            "email": email,
            "linkedin": linkedin,
            "twitter": twitter,
            "industry": industry,
            "rounds": rounds,
            "investment_range": investment_range,
            "location": location,
            "notable_investments": notable_investments,
        }
        investor_list.append(investor)
    with open("investor_list.json", "w") as file:
        file.write(json.dumps(investor_list, indent=4))


@cli.command()
@click.option(
    "--column",
    prompt="Enter a column name for the data that should be sanitized",
    help="Column for the data",
    required=True,
)
@click.option(
    "--extra",
    prompt="Enter the extra data that should be removed from the column with ';' as a separator if needed",
    help="Column for the extra data",
    required=True,
)
@click.argument("file", type=click.File("r+"), required=True)
def sanitize_data(file, column, extra):
    """Sanitize the data in the column"""

    investor_list = json.load(file)

    for investor in investor_list:
        for ex in extra.split(";"):
            investor[column] = investor[column].replace(ex, "").replace("  ", " ").strip()

    with open("investor_list.json", "w") as file:
        file.write(json.dumps(investor_list, indent=4))


# @cli.command()
# @click.argument("file", type=click.File("r"), required=True)
# def populate_db(file):
#     """Populate the database with the data from the json file"""
#     investor_list = json.load(file)
#     for investor in investor_list:
#         industries = get_industries(investor.get("industry"))
#         min_investment, max_investment = get_min_max_investment(investor.get("investment_range"))
#         rounds = get_rounds(investor.get("rounds"))
#         notable_investments = get_notable_investments(investor.get("notable_investments"))

#         investor = Investor(
#             first_name=investor.get("first_name"),
#             last_name=investor.get("last_name"),
#             firm_name=investor.get("firm_name"),
#             position=investor.get("position"),
#             about=investor.get("about"),
#             email=investor.get("email"),
#             linkedin=investor.get("linkedin"),
#             twitter=investor.get("twitter"),
#             location=investor.get("location"),
#             min_investment=min_investment,
#             max_investment=max_investment,
#             industries=industries,
#             rounds=rounds,
#             notable_investments=notable_investments,
#         )
#         db.session.add(investor)
#     db.session.commit()


if __name__ == "__main__":
    cli()


# r = [
#     {
#         "first_name": "Aaref",
#         "last_name": "Hilaly",
#         "firm_name": "Bain Capital Ventures",
#         "position": "Partner",
#         "about": None,
#         "email": "ahilaly@baincapital.com",
#         "linkedin": "https://www.linkedin.com/in/aarefhilaly/",
#         "twitter": "https://twitter.com/aaref",
#         "industry": "Analytics,Enterprise,Hardware,B2B SaaS,SMB Software,AI,Cloud,Social Media,Cloud Infrastructure,SaaS,Social Networks,Generalist,Developer Tools,B2C/E-Commerce,FinTech,Marketplaces",
#         "rounds": "Seed,Series A,Series B+",
#         "investment_range": "$1M - $3M,$3M - $10M,$10M - $50M,$50M+,$500K - $1M",
#         "location": "San Francisco, California",
#         "notable_investments": "ThousandEyes,Clari,LightStep,StackRox,Remix,Skyhigh Networks,Keen,NimbleRx,Tecton",
#     },
#     {
#         "first_name": "Aaron",
#         "last_name": "Stachel",
#         "firm_name": "FirstMile Ventures",
#         "position": "Partner",
#         "about": None,
#         "email": "aaron@firstmilevc.com",
#         "linkedin": "https://www.linkedin.com/in/aaronstachel/",
#         "twitter": "https://twitter.com/AaronStachel",
#         "industry": "Generalist,Enterprise,Web3",
#         "rounds": "Seed",
#         "investment_range": "",
#         "location": "Denver, Colorado",
#         "notable_investments": "",
#     },
#     {
#         "first_name": "Abe",
#         "last_name": "Yokell",
#         "firm_name": "Congruent Ventures",
#         "position": "Managing Partner",
#         "about": None,
#         "email": "abe@congruentvc.com",
#         "linkedin": "https://www.linkedin.com/in/abe-yokell/",
#         "twitter": "https://twitter.com/CleanVC",
#         "industry": "Data Services,B2B SaaS,AI,Climate,Energy,Food & Ag,Hardware,Enterprise,Consumer,DeepTech,FinTech",
#         "rounds": "Series A,Seed,Series B+,Pre-seed",
#         "investment_range": "$100K - $500K,$500K - $1M,$0 - $100K,$1M - $3M,$3M - $10M",
#         "location": "San Francisco, California",
#         "notable_investments": "AMP Robotics,Amply Power,Blueprint Power,Omnidian,Renovate America,Qnovo,EcoFactor,Flywheel Software",
#     },
# ]
