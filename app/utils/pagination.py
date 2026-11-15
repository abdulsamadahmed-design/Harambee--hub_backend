from flask import request


DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100


def _get_positive_integer(parameter, default):
    """
    Read and validate a positive integer from the request query string.
    """
    value = request.args.get(parameter)

    if value is None:
        return default

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("{} must be a valid integer".format(parameter))

    if number < 1:
        raise ValueError("{} must be at least 1".format(parameter))

    return number


def paginate_query(query, serializer=None):
    """
    Paginate a SQLAlchemy query.

    Returns a dictionary containing:
    items, page, per_page, total and pages.

    An optional serializer converts each database object into a
    JSON-ready dictionary.
    """
    page = _get_positive_integer("page", DEFAULT_PAGE)
    per_page = _get_positive_integer("per_page", DEFAULT_PER_PAGE)

    per_page = min(per_page, MAX_PER_PAGE)

    total = query.count()

    records = (
        query
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    if serializer is not None:
        items = [serializer(record) for record in records]
    else:
        items = records

    pages = (total + per_page - 1) // per_page

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages
    }
