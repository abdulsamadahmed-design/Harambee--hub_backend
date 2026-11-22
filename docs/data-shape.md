# Harambee Hub API Data Shapes

## 1. Purpose

This document describes the known API resources, data structures, pledge serialization, and pagination behavior in the Harambee Hub backend.

It is based on the supplied OpenAPI endpoint listing and the following backend source files:

- `app/models/pledge.py`
- `app/utils/pagination.py`
- `docs/openapi.yaml`

Where the supplied excerpts do not establish a field or behavior, it is explicitly marked as **Not established by the supplied excerpts**.

---

## 2. API Endpoint Overview

The supplied OpenAPI listing identifies the following endpoints.

### Health

| Method | Endpoint |
|---|---|
| GET | `/api/health` |

### Authentication

| Method | Endpoint |
|---|---|
| POST | `/api/auth/register` |
| GET | `/api/auth/verify-email/{token}` |
| POST | `/api/auth/login` |
| GET | `/api/auth/me` |
| POST | `/api/auth/change-password` |

### Campaigns

| Method | Endpoint |
|---|---|
| GET | `/api/campaigns/` |
| POST | `/api/campaigns/` |
| GET | `/api/campaigns/{campaign_id}` |

### Pledges

| Method | Endpoint |
|---|---|
| GET | `/api/pledges/campaign/{campaign_id}` |
| POST | `/api/pledges/campaign/{campaign_id}` |
| GET | `/api/pledges/mine` |
| GET | `/api/pledges/campaign/{campaign_id}/manage` |
| GET | `/api/pledges/{pledge_id}` |
| PATCH | `/api/pledges/{pledge_id}` |
| DELETE | `/api/pledges/{pledge_id}` |
| POST | `/api/pledges/{pledge_id}/confirm` |
| POST | `/api/pledges/{pledge_id}/remind` |

### Administration

| Method | Endpoint |
|---|---|
| GET | `/api/admin/users` |
| GET | `/api/admin/dashboard` |

The endpoint listing establishes the available paths and HTTP methods. Individual request fields, response schemas, authorization requirements, and error responses are not established by the supplied endpoint listing alone.

---

## 3. Pledge Data Model

The Pledge model is defined in `app/models/pledge.py`.

Its database table is named `pledges`.

### 3.1 Fields

| Field | Database type | Nullable | Description |
|---|---|---|---|
| `id` | Integer | No | Primary key |
| `campaign_id` | Integer | No | Foreign key referencing `campaign.id`; indexed |
| `contributor_id` | Integer | Yes | Foreign key referencing `user.id`; indexed |
| `contributor_name` | String(100) | Yes | Contributor name stored on the pledge |
| `amount` | Numeric(12, 2) | No | Pledged amount |
| `message` | String(500) | Yes | Optional pledge message |
| `is_anonymous` | Boolean | No | Defaults to `false` |
| `status` | String(20) | No | Defaults to `pending`; indexed |
| `created_at` | DateTime | No | Defaults to the current UTC time |
| `confirmed_at` | DateTime | Yes | Confirmation timestamp |

### 3.2 Pledge statuses

The model defines these valid status values:

- `pending`
- `confirmed`
- `cancelled`

The default status is `pending`.

### 3.3 Relationships

The model defines two relationships:

- `campaign`: relationship to the Campaign model.
- `contributor`: relationship to the User model.

The campaign foreign key references `campaign.id`. The contributor foreign key references `user.id`.

---

## 4. Pledge Serialization

The Pledge model provides:

```python
to_dict(viewer=None)
```

This method returns a JSON-ready dictionary containing:

| Response field | Source | Format |
|---|---|---|
| `id` | Pledge ID | Integer |
| `campaign_id` | Campaign foreign key | Integer |
| `amount` | Pledge amount | Float |
| `message` | Pledge message | String or null |
| `status` | Pledge status | String |
| `created_at` | Creation timestamp | ISO-formatted string or null |
| `confirmed_at` | Confirmation timestamp | ISO-formatted string or null |
| `contributor` | Contributor summary | Object or null |

The `amount` field is converted from the database Numeric value to a Python float.

Datetime values are serialized using `isoformat()`.

### 4.1 Example pledge response

The following is an illustrative example of the shape returned by `to_dict()`. The values are examples, not actual database records.

```json
{
  "id": 12,
  "campaign_id": 4,
  "amount": 2500.00,
  "message": "Happy to support this campaign.",
  "status": "pending",
  "created_at": "2026-11-22T09:30:00+00:00",
  "confirmed_at": null,
  "contributor": {
    "id": 7,
    "name": "Example Contributor"
  }
}
```

### 4.2 Contributor summary

The `_contributor_summary()` method determines the contributor object.

Its behavior is:

1. If `contributor_name` is present, return that name together with `contributor_id`.
2. Otherwise, if a related contributor exists, return the contributor's ID and name.
3. The related contributor's `name` is preferred; `username` is used as a fallback.
4. If no related contributor exists, return `null`.

The contributor object has this shape:

```json
{
  "id": 7,
  "name": "Example Contributor"
}
```

If neither a stored contributor name nor a related contributor is available:

```json
{
  "contributor": null
}
```

**Important:** Although the model contains `is_anonymous`, the supplied `to_dict()` implementation does not use this field to change the contributor summary. Any additional anonymity filtering elsewhere is not established by the supplied excerpts.

The `viewer` argument is accepted by `to_dict()`, but its effect is not established by the supplied implementation.

---

## 5. Pagination

Pagination is implemented in:

```text
app/utils/pagination.py
```

The helper function is:

```python
paginate_query(query, serializer=None)
```

It paginates a SQLAlchemy query and returns a dictionary.

### 5.1 Query parameters

| Parameter | Default | Minimum | Maximum |
|---|---:|---:|---:|
| `page` | 1 | 1 | Not specified |
| `per_page` | 10 | 1 | 100 |

Both parameters must be positive integers.

Invalid integer values raise a `ValueError`.

Values below 1 also raise a `ValueError`.

The `per_page` value is capped at 100.

### 5.2 Pagination response shape

The helper returns:

```json
{
  "items": [],
  "page": 1,
  "per_page": 10,
  "total": 0,
  "pages": 0
}
```

| Field | Description |
|---|---|
| `items` | Records returned for the requested page |
| `page` | Current page number |
| `per_page` | Number of records requested per page, capped at 100 |
| `total` | Total number of records matching the query |
| `pages` | Total number of pages |

The number of pages is calculated as:

```python
pages = (total + per_page - 1) // per_page
```

An empty result set therefore produces zero pages.

### 5.3 Serialization

The optional `serializer` argument converts each database record into a JSON-ready representation.

For example:

```python
paginate_query(query, serializer=lambda record: record.to_dict())
```

Without a serializer, the helper returns the query records directly.

### 5.4 Example request

```http
GET /api/campaigns/?page=2&per_page=10
```

The pagination helper supports these query parameters. Whether every listed endpoint uses this helper is not established by the supplied excerpts.

---

## 6. Authentication and Token Handling

The frontend API client shown in the supplied project context:

- Stores the authentication token in browser `localStorage` under the key `token`.
- Reads the token before making API requests.
- Sends the token using the HTTP `Authorization` header in Bearer format.

Example:

```http
Authorization: Bearer <token>
```

The backend endpoint listing includes registration, login, email verification, current-user, and password-change endpoints.

The exact token response schema, token expiration behavior, refresh mechanism, and authorization rules for individual endpoints are not established by the supplied excerpts.

---

## 7. Data Shape Verification Notes

The following details are confirmed by the supplied source excerpts:

- Pledge database fields and relationships.
- Pledge valid status values and default status.
- Pledge serialization through `to_dict()`.
- Contributor summary behavior.
- Pagination parameter defaults and validation.
- Pagination response fields and page calculation.
- Listed API endpoint paths and HTTP methods.

The following details still require inspection of the complete OpenAPI schemas or corresponding route implementations:

- Campaign request and response fields.
- Registration and login request and response fields.
- Authentication error response structures.
- Pledge creation and update request schemas.
- Whether anonymous pledges are filtered in endpoint responses.
- Whether all list endpoints use `paginate_query()`.
- Authorization requirements for individual endpoints.
- Exact response envelopes and HTTP status codes.
- Behavior of confirmation and reminder endpoints.
- Full User, Campaign, and Admin Dashboard data structures.

---

## 8. Source Files

This document is based on:

```text
docs/openapi.yaml
app/models/pledge.py
app/utils/pagination.py
```

For future updates, keep this document aligned with the actual model definitions, route implementations, serializers, and OpenAPI schemas. When an API response or field changes, update the corresponding section here as well.
