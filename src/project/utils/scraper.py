import csv
from itertools import islice

from thefuzz import fuzz

from ..extensions import db
from ..models.helpers import Round


def get_min_max_investment(
    check_size_string: str,
) -> tuple[int, int] | tuple[int, None] | tuple[None, int] | tuple[None, None]:
    range_set = set()
    for range_ in check_size_string.split(","):
        sanitized_range = (
            range_.replace("$", "")
            .replace(",", " ")
            .replace(" ", "")
            .replace("K", "000")
            .replace("M", "000000")
            .replace("B", "000000000")
            .replace("+", "")
        )
        if "-" in sanitized_range:
            min_investment, max_investment = sanitized_range.split("-")
            range_set.add(int(min_investment))
            range_set.add(int(max_investment))
        else:
            if sanitized_range in ["", " "]:
                continue
            range_set.add(int(sanitized_range))
    min_investment, max_investment = None, None
    if len(range_set) > 1:
        min_investment, max_investment = min(range_set), max(range_set)
    elif len(range_set) == 1:
        max_investment = range_set.pop()
    return min_investment, max_investment


def get_rounds(rounds: str) -> list[Round]:
    round_list = []
    for round_ in rounds.split(","):
        for r in Round.get_all():
            if round_ == "Series B+":
                round_list.append(Round.get_by_name("Series B"))
                round_list.append(Round.get_by_name("Series C"))
                break
            if r and fuzz.ratio(round_.lower(), r.name.lower()) > 90:
                round_ = r
                round_list.append(round_)
                break
    return list(set(round_list))


def get_notable_investments(existing_notable_investments, notable_investments_cls, notable_investments: str) -> list:
    notable_investment_list = []
    for notable_investment in notable_investments.split(","):
        existing = None
        for eni in existing_notable_investments:
            if fuzz.ratio(notable_investment, eni.name) > 90:
                existing = eni
                break
        if existing:
            notable_investment_list.append(existing)
        else:
            ni = notable_investments_cls(name=notable_investment)
            db.session.add(ni)
            notable_investment_list.append(ni)
    return list(set(notable_investment_list))


def populate_demo(notable_investments_cls, industry_cls, file_name="data/investor.csv"):
    existing_notable_investments = notable_investments_cls.get_all()
    existing_industry_list = industry_cls.get_industry_list()
    investor_list = []
    with open(file_name, newline="") as file:
        reader = csv.reader(file, delimiter=";")
        for row in islice(reader, 1, None):
            min_investment, max_investment = get_min_max_investment(row[8])

            industry_list = []
            for industry in row[5].split(","):
                for i in existing_industry_list:
                    if i and fuzz.ratio(industry, i.name) > 80:
                        industry = i
                        industry_list.append(industry)
                        break

            round_list = get_rounds(row[9])

            notable_investment_list = get_notable_investments(
                existing_notable_investments, notable_investments_cls, row[10]
            )

            investor = {
                "first_name": row[0].split(" ")[0],
                "last_name": row[0].split(" ")[1],
                "firm_name": row[1],
                "position": row[2],
                "email": row[3],
                "location": row[4],
                "coordinates": row[4],
                "industries": list(set(industry_list)),
                "linkedin": row[6],
                "twitter": row[7],
                "min_investment": min_investment,
                "max_investment": max_investment,
                "rounds": round_list,
                "notable_investments": notable_investment_list,
            }
            investor_list.append(investor)
        return investor_list


def populate_blockchain(notable_investments_cls, industry_cls, file_name="data/globalify - blockchain.csv"):
    investor_list = []
    with open(file_name, newline="") as file:
        existing_notable_investments = notable_investments_cls.get_all()
        existing_industry_list = industry_cls.get_industry_list()
        reader = csv.reader(file, delimiter=";")

        for row in islice(reader, 1, None):
            first_name = row[0].split(" ")[0]

            if len(row[0].split(" ")) == 1:
                last_name = None
            else:
                last_name = row[0].split(" ")[1]

            firm_name = row[1].replace('"', "")

            industries = row[7].split(",")
            industry_list = []
            for industry in industries:
                if "—" in industry:
                    industry = industry.split(" — ")[1]
                industry = (
                    industry.replace(")", "")
                    .replace("(", "")
                    .replace(" Commerce", " ")
                    .replace("Smart Tech", " ")
                    .replace("Money Tech", "")
                    .replace("Health Tech", "")
                    .strip()
                )
                for i in existing_industry_list:
                    if i and fuzz.ratio(industry, i.name) > 80:
                        industry = i
                        industry_list.append(industry)
                        break

            min_investment, max_investment = get_min_max_investment(row[13])
            round_list = get_rounds(row[14])
            notable_investment_list = get_notable_investments(
                existing_notable_investments, notable_investments_cls, row[15]
            )

            investor = {
                "first_name": first_name,
                "last_name": last_name,
                "firm_name": firm_name,
                "position": row[2],
                "about": row[22],
                "email": row[4],
                "location": row[6],
                "coordinates": row[6],
                "industries": list(set(industry_list)),
                "linkedin": row[9],
                "twitter": row[11],
                "min_investment": min_investment,
                "max_investment": max_investment,
                "rounds": round_list,
                "notable_investments": notable_investment_list,
            }
            investor_list.append(investor)
        return investor_list


def add_https_prefix(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url
