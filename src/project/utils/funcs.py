import hashlib


def generate_pagination(current_page: int, total_pages: int, around_count: int = 2) -> dict:
    start_pages = range(1, min(3, total_pages + 1))
    around_pages = range(max(1, current_page - around_count), min(current_page + around_count + 1, total_pages + 1))
    end_pages = range(max(current_page + around_count + 1, total_pages - 1), total_pages + 1)
    pages = list(start_pages)

    if not pages:
        return {
            "current_page": 0,
            "prev": 0,
            "next": 0,
            "pages": [],
            "has_other_pages": False,
            "has_prev": False,
            "has_next": False,
        }

    if around_pages and around_pages[0] - pages[-1] > 1:
        pages.append(0)
    pages.extend(p for p in around_pages if p not in pages)
    if end_pages and end_pages[0] - pages[-1] > 1:
        pages.append(0)
    pages.extend(p for p in end_pages if p not in pages)

    return {
        "current_page": current_page,
        "prev": max(1, current_page - 1),
        "next": min(current_page + 1, total_pages),
        "last_page": total_pages,
        "pages": around_pages,
        "has_other_pages": bool(len(around_pages) > 1),
        "has_prev": bool(current_page > 1),
        "has_next": bool(current_page < total_pages),
    }


def calculate_md5(data: bytes):
    """Calculates the MD5 hash of a file."""
    hash_md5 = hashlib.md5(data).hexdigest()
    return hash_md5


def normalize_name(name):
    """Normalize names by capitalizing and replacing underscores with spaces."""
    return name.replace("_", " ").title()
