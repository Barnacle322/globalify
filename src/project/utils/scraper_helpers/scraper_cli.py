import csv
import json
from itertools import islice

import click


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    ctx.obj = {}
    if ctx.invoked_subcommand is None:
        ctx.invoke(get_indices)
        ctx.invoke(set_columns)
        if ctx.obj.get("sanitize") == "y":
            ctx.invoke(sanitize_data)


@cli.command()
@click.pass_context
def get_indices(ctx):
    """Show indices for every attribute in csv file"""
    ctx.obj["file"] = click.prompt("Enter a file name", type=str)
    ctx.obj["delimiter"] = click.prompt("Enter a delimiter for the file", default=";", show_default=True, type=str)
    with open(ctx.obj.get("file")) as f:
        reader = csv.reader(f, delimiter=ctx.obj.get("delimiter"))
        headers = next(reader)
        ctx.obj["headers"] = ""
        for index, header in enumerate(headers):
            ctx.obj["headers"] += f"<{header}> column has index <{index}>\n"


@cli.command()
@click.pass_context
def set_columns(ctx):
    """Set the attributes for database from the csv file"""
    click.echo(ctx.obj.get("headers"))
    start_row = click.prompt("Enter a start row for the file", default=1, show_default=True, type=int)
    column_name = click.prompt(
        "Enter a column number of full name. If first name and last name are in separated columns, enter numbers with a space between them ' '",
        type=str,
    )
    column_firm_name = click.prompt("Enter a column number of the firm name", default="", show_default=True, type=str)
    column_position = click.prompt("Enter a column number of the position", default="", show_default=True, type=str)
    column_about = click.prompt("Enter a column number of the about", default="", show_default=True, type=str)
    column_email = click.prompt("Enter a column number of the email", default="", show_default=True, type=str)
    column_linkedin = click.prompt("Enter a column number of the linkedin", default="", show_default=True, type=str)
    column_twitter = click.prompt("Enter a column number of the twitter", default="", show_default=True, type=str)
    column_industry = click.prompt("Enter a column number of the industry", default="", show_default=True, type=str)
    column_rounds = click.prompt("Enter a column number of the rounds", default="", show_default=True, type=str)
    column_investment_range = click.prompt(
        "Enter a column number of the investment range or column numbers of minimum and maximum investment sums separated by a space ' '",
        default="",
        show_default=True,
        type=str,
    )
    column_location = click.prompt("Enter a column number of the location", default="", show_default=True, type=str)
    column_notable_investments = click.prompt(
        "Enter a column number of the notable investments", default="", show_default=True, type=str
    )
    investor_list = []
    with open(ctx.obj.get("file"), encoding="utf-8-sig") as file:
        reader = csv.reader(file, delimiter=ctx.obj.get("delimiter"))
        for row in islice(reader, start_row, None):
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
                    row[int(column_investment_range.split(" ")[0])]
                    + "-"
                    + row[int(column_investment_range.split(" ")[1])]
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
    with open("investor_list.json", "w", encoding="utf-8-sig") as file:
        file.write(json.dumps(investor_list, indent=4))
    click.echo("The columns were set successfully.")

    sanitize = click.prompt(
        "Do you need to sanitize the file? Enter 'y' for yes and 'n' for no.",
        type=click.Choice(["y", "n"]),
        default="n",
    )
    ctx.obj["sanitize"] = sanitize


@cli.command()
@click.option(
    "--column",
    prompt="Enter a column name for the data that should be sanitized",
    help="Column name for the data",
    required=True,
)
@click.option(
    "--extra",
    prompt="Enter the extra data that should be removed from the column with ';' as a separator if needed",
    help="Extra data for deletion from the column. Use ';' as a separator",
    required=True,
)
def sanitize_data(column, extra):
    """Sanitize the data in the column"""
    try:
        with open("investor_list.json", encoding="utf-8-sig") as file:
            investor_list = json.load(file)

            for investor in investor_list:
                for ex in extra.split(";"):
                    investor[column] = investor[column].replace(ex, "").replace("  ", " ").strip()

            with open("investor_list.json", "w", encoding="utf-8-sig") as file:
                file.write(json.dumps(investor_list, indent=4))
    except Exception as e:
        click.echo(f"An error occurred: {e}")


@cli.command()
@click.option(
    "--answer",
    prompt="Are you sure you want to empty the file 'investor_list.json'? Enter 'y' for yes and 'n' for no.",
    help="Command to empty the file 'investor_list.json'",
    type=click.Choice(["y", "n"]),
    required=True,
)
def empty_file(answer):
    """Empty the file"""
    with open("investor_list.json", "w", encoding="utf-8-sig") as file:
        if answer == "y":
            json.dump({}, file)
        else:
            click.echo("The file was not emptied.")


if __name__ == "__main__":
    cli()
