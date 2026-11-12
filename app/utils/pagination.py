def paginate(query, page=1, per_page=10, serializer=lambda item: item):
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 10), 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        "items": [serializer(item) for item in pagination.items],
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }
