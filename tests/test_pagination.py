import pytest
from flask import Flask

from app.utils.pagination import paginate_query


class FakeQuery:
    """A simple query substitute for testing pagination."""

    def __init__(self, records):
        self.records = records
        self.limit_value = None
        self.offset_value = None

    def count(self):
        return len(self.records)

    def limit(self, value):
        self.limit_value = value
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def all(self):
        start = self.offset_value
        end = start + self.limit_value
        return self.records[start:end]


@pytest.fixture
def app():
    return Flask(__name__)


@pytest.fixture
def records():
    return [{"id": number} for number in range(1, 26)]


def test_default_pagination(app, records):
    query = FakeQuery(records)

    with app.test_request_context("/?"):
        result = paginate_query(query)

    assert result["page"] == 1
    assert result["per_page"] == 10
    assert result["total"] == 25
    assert result["pages"] == 3
    assert len(result["items"]) == 10
    assert result["items"][0]["id"] == 1


def test_custom_page_and_per_page(app, records):
    query = FakeQuery(records)

    with app.test_request_context("/?page=2&per_page=5"):
        result = paginate_query(query)

    assert result["page"] == 2
    assert result["per_page"] == 5
    assert result["items"] == [
        {"id": 6},
        {"id": 7},
        {"id": 8},
        {"id": 9},
        {"id": 10}
    ]


def test_per_page_is_capped_at_100(app):
    query = FakeQuery([{"id": number} for number in range(1, 151)])

    with app.test_request_context("/?per_page=200"):
        result = paginate_query(query)

    assert result["per_page"] == 100
    assert len(result["items"]) == 100
    assert result["total"] == 150
    assert result["pages"] == 2


def test_empty_results(app):
    query = FakeQuery([])

    with app.test_request_context("/"):
        result = paginate_query(query)

    assert result["items"] == []
    assert result["page"] == 1
    assert result["per_page"] == 10
    assert result["total"] == 0
    assert result["pages"] == 0


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("page", "abc"),
        ("per_page", "abc"),
        ("page", "0"),
        ("per_page", "0"),
        ("page", "-1"),
        ("per_page", "-5")
    ]
)
def test_invalid_pagination_values(app, parameter, value):
    query = FakeQuery([])

    with app.test_request_context("/?{}={}".format(parameter, value)):
        with pytest.raises(ValueError):
            paginate_query(query)


def test_serializer_converts_records(app, records):
    query = FakeQuery(records)

    with app.test_request_context("/?per_page=2"):
        result = paginate_query(
            query,
            serializer=lambda record: "User {}".format(record["id"])
        )

    assert result["items"] == ["User 1", "User 2"]


def test_page_beyond_available_results(app, records):
    query = FakeQuery(records)

    with app.test_request_context("/?page=10&per_page=5"):
        result = paginate_query(query)

    assert result["items"] == []
    assert result["page"] == 10
    assert result["total"] == 25
    assert result["pages"] == 5
