from thefuzz import fuzz

from ...extensions import db
from ...models.helpers import Round


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
    for round_ in rounds:
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


def get_notable_investments(notable_investments: str, existing_notable_investments, notable_investments_cls) -> list:
    notable_investment_list = []
    for notable_investment in notable_investments.split(","):
        existing = None
        for eni in existing_notable_investments:
            if fuzz.ratio(notable_investment, eni.name) > 99:
                existing = eni
                break
        if existing and existing != "":
            notable_investment_list.append(existing)
        else:
            if notable_investment != "":
                ni = notable_investments_cls(name=notable_investment)
                db.session.add(ni)
                notable_investment_list.append(ni)
    return list(set(notable_investment_list))


def get_industries(industries: str, existing_industries) -> list:
    industry_list = []
    for industry in industries.split(","):
        if "—" in industry:
            industry = industry.split(" — ")[1]
        industry = industry.strip()
        for i in existing_industries:
            if i and fuzz.ratio(industry, i.name) > 80:
                industry = i
                industry_list.append(industry)
                break
    return list(set(industry_list))
