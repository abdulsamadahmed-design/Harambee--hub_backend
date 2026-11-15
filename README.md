# Harambee Hub - Backend API

REST API for Harambee Hub, a fundraising platform that replaces WhatsApp contribution lists. Organizers create campaigns, contributors pledge amounts, and the platform tracks who has actually paid. Roles: **organizer**, **contributor**, **admin**.

Built with Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended and Marshmallow, with SendGrid for email and Cloudinary for images. The React frontend lives in a separate repository and talks to this API over HTTP/JSON.

Last updated: 15 Nov 2026. Update this file in the same PR as any change that affects setup, structure, endpoints or ownership.

---

## 1. Rules for the whole team (read first)

### Never push or merge to `main`
- **Do not push to `main`. Do not merge into `main`.** Only the Scrum master merges `develop` into `main`, through a reviewed pull request, when `develop` is stable and demo-ready.
- **Do not push directly to `develop` either.** All work goes through a feature branch and a pull request (PR).
- Never use `git push --force` on a shared branch.
- Work only on tasks that have a card on the Trello board.

### Branch workflow (Gitflow)
| Branch | Purpose |
|--------|---------|
| `main` | Stable, demo-ready code only |
| `develop` | Integration branch where finished work is combined |
| `feature/<area>-<short-name>` | One task, for example `feature/pledges-reminders` |
| `fix/<short-name>`, `docs/<short-name>`, `test/<short-name>` | Fixes, documentation-only changes, test-only changes |

Steps for every task:
1. `git checkout develop` then `git pull` - switch to `develop` and download the latest changes.
2. `git checkout -b feature/<area>-<short-name>` - create your own branch from `develop`.
3. Work and commit in small steps (see commit messages below).
4. `git push -u origin feature/<area>-<short-name>` - upload your branch.
5. On GitHub, open a PR **into `develop`**. Check the base branch, because GitHub may default to `main`. Write a description: what changed and how to test it.
6. Get one review from a teammate who did not write the code (see the review ring in section 2). The Scrum master merges.
7. Bring in the latest work every morning: `git fetch origin`, then `git merge origin/develop` while on your branch.

### Commit messages
Format: `type: short description`, present tense, one idea per commit.
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
Examples: `feat: add resend verification route`, `fix: return 404 for missing campaign`, `test: cover pledge validation`.

### Pull request checklist
- [ ] App starts, and `pytest` passes locally
- [ ] New code has tests, including failure cases (wrong role, bad input, missing token)
- [ ] No secrets, `.env` files, `venv/` or `*.db` files committed
- [ ] List endpoints are paginated
- [ ] Input is validated and errors return the standard JSON shape (section 9)
- [ ] You only changed files you own, or agreed the change with the owner. **Do not edit `.gitignore` in a feature PR.**
- [ ] Any new migration is the only new head (`flask --app run db heads` prints one line)
- [ ] The endpoint table in this README and `docs/openapi.yaml` are updated for any route you added or changed
- [ ] PR description says what changed and how to test it

### Do not create `app.py`, or a `Pipfile`
- The project has an `app/` folder. A file called `app.py` next to it clashes, because Python imports the folder and ignores the file. The entry point is `run.py`.
- We use **`venv` + `requirements.txt`**. Do not add a `Pipfile` or `Pipfile.lock`, because two dependency lists drift apart.

---

## 2. Team and file ownership

Everyone builds a complete slice (model, validation, routes, tests) and explains it at the stand-ups. Everyone must understand the whole project, so read the other slices' PRs.

| Member | Name | Slice | Files you own |
|--------|------|-------|---------------|
| **M1 (Scrum master)** | | Login validation, test setup, CI, docs, deployment | `app/schemas/auth_schema.py`, `app/utils/decorators.py`, `tests/conftest.py`, `.github/workflows/ci.yml`, `docs/`, deployment files, `README.md`; reviews and merges all PRs |
| **M2** | | Registration and email | `app/routes/registration_routes.py`, `app/schemas/registration_schema.py`, `app/utils/email.py`, `tests/test_registration.py`, `tests/test_email.py` |
| **M3** | | Campaigns and image upload | `app/models/campaign.py`, `app/routes/campaign_routes.py`, `app/schemas/campaign_schema.py`, `app/utils/uploads.py`, `tests/test_campaigns.py`, `tests/test_uploads.py` |
| **M4** | | Pledges | `app/models/pledge.py`, `app/routes/pledge_routes.py`, `app/schemas/pledge_schema.py`, `tests/test_pledges.py` |
| **M5** | | Admin and shared tools | `app/routes/admin_routes.py`, `app/utils/pagination.py`, `seed.py`, `tests/test_admin.py`, `tests/test_pagination.py` |
| **M6** | | Foundation, users and login | `run.py`, `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/models/user.py`, `app/models/__init__.py`, `app/routes/auth_routes.py`, `app/utils/errors.py`, `.env.example`, `migrations/` setup |

Fill in the Name column.

### Review ring
Every PR needs one reviewer who did not write it: M1 reviews M2, M2 reviews M3, M3 reviews M4, M4 reviews M5, M5 reviews M6, and M6 reviews M1. The Scrum master then does the final check and merge.

### Shared files, with rules
- `app/__init__.py` (M6): each member adds only the import and `register_blueprint` line for their own blueprint.
- `app/models/__init__.py`: each model owner adds **one import line** for their own model and nothing else.
- `requirements.txt`: add only your package's line, **pinned to a version** (for example `sendgrid==6.12.5`). **Do not run `pip freeze > requirements.txt`** on a feature branch, because it rewrites the whole file and causes conflicts.
- `.env.example`: add only the variable names for your own feature. Never put real values in it.
- `migrations/`: see section 7.
- Need a change in a file you don't own? Ask the owner, or send a tiny separate PR.

---

## 3. Where we are and what is left

Merged into `develop` (files and migrations are present):
- App factory, config, extensions, error handlers, `User` model, login, `/me`, change-password (M6)
- Registration with email verification and the SendGrid email utility (M2)
- Campaigns with image upload (M3)
- Pledges (M4)
- Pagination helper and admin routes (M5)
- Test setup, login schema, decorators and CI (M1)

Still to do (tick them off as they land, and add owners):
- [ ] Docs PR merged (database diagram, API spec, deployment guide)
- [ ] Docs match the real code: statuses, field names and endpoint paths for campaigns and pledges
- [ ] Login blocks unverified emails (returns `403` until `email_verified` is true)
- [ ] Resend-verification route, for failed emails and expired links
- [ ] `seed.py` creates an admin account and sample data
- [ ] Backend coverage at 60% or more (`pytest --cov=app`)
- [ ] Deployment: `gunicorn` and `psycopg2-binary` in `requirements.txt`, health route, CORS for the frontend address
- [ ] Frontend repository connected to this API
- [ ] Final README pass: team names, links, screenshots

---

## 4. First-time setup

Requirements: Python 3.10 or newer, Git. Windows users: use WSL or Git Bash.

```bash
# 1. Clone and enter the project (stay in the repo root for every command)
git clone <repo-url>
cd <repo-folder>

# 2. Switch to develop
git checkout develop
git pull

# 3. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows PowerShell: venv\Scripts\Activate.ps1

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create your .env file
cp .env.example .env              # then open .env and fill in the values (see section 5)

# 6. Create the database tables
flask --app run db upgrade

# 7. (Optional) load sample data
python seed.py

# 8. Run the server
flask --app run run --debug
```

The API is now at `http://127.0.0.1:5000`. Print every route with `flask --app run routes`.

Every time you open a new terminal: `cd` into the repo root and run `source venv/bin/activate` again. If your prompt does not start with `(venv)`, the environment is not active.

### Installing dependencies
- Install everything the project needs: `pip install -r requirements.txt`
- After pulling changes that touched `requirements.txt`, run that command again.
- Adding a library: `pip install <package>`, add its pinned line to `requirements.txt` by hand (see the shared file rules in section 2), and mention it in your PR.

### Trying the API in Postman
- Use the **Postman desktop app**, or the **Desktop Agent**. The Cloud Agent cannot reach `127.0.0.1`.
- Use the full address, for example `http://127.0.0.1:5000/api/auth/login`.
- For requests with a body: **Body > raw > JSON**. For protected routes: **Authorization > Bearer Token**, and paste the token from login.

---

## 5. Environment variables

Create `.env` from `.env.example`. **`.env` is ignored by Git and must never be committed.** If a secret is ever pushed, treat it as leaked and replace it.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | Key used to sign login tokens (there is no default, the app must fail if it is missing) |
| `DATABASE_URL` | Database address, for example `sqlite:///harambee.db` for local development |
| `SENDGRID_API_KEY` | SendGrid key for sending email |
| `SENDGRID_FROM_EMAIL` | Verified sender address in SendGrid |
| `FRONTEND_URL` | Address of the frontend (used for links in emails and for CORS). Local Vite default: `http://localhost:5173` |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Image uploads |

Generate a strong secret with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Use different values for `SECRET_KEY` and `JWT_SECRET_KEY`. Each teammate and production get their own values. Without the SendGrid or Cloudinary keys, registration still works but no email is sent, and uploads fail.

---

## 6. Project structure

```
.
|-- app/
|   |-- __init__.py          # create_app() application factory, registers blueprints
|   |-- config.py            # settings loaded from .env
|   |-- extensions.py        # db, migrate, jwt, cors created here (no app yet)
|   |-- models/              # user.py, campaign.py, pledge.py
|   |-- routes/              # blueprints: auth, registration, campaign, pledge, admin
|   |-- schemas/             # Marshmallow validation schemas
|   `-- utils/               # decorators, errors, pagination, email, uploads
|-- migrations/              # Flask-Migrate, committed to Git
|-- tests/                   # pytest tests, one file per slice, shared setup in conftest.py
|-- docs/                    # database.md, openapi.yaml, deployment.md
|-- .github/workflows/       # ci.yml
|-- run.py                   # entry point: app = create_app()
|-- seed.py                  # sample data
|-- requirements.txt
|-- pytest.ini
|-- render.yaml
|-- .env.example
|-- .gitignore
`-- README.md
```

---

## 7. Database and migrations

Tables are defined as models in `app/models/`. Never edit the database by hand. Change the models, then create a migration.

```bash
flask --app run db migrate -m "describe the change"   # generate a migration from model changes
flask --app run db upgrade                            # apply migrations to your database
flask --app run db heads                              # must print exactly ONE head
```

- `db init` was already run, **never run it again.** After pulling, just run `db upgrade`.
- Pull `develop` **before** you run `db migrate`, and read the generated file in `migrations/versions/` before applying it.
- Two people generating migrations from the same starting point creates two "heads" and the database commands fail. Merge migration PRs one at a time, and tell the Scrum master if `db heads` shows two lines. Never edit an old migration file.
- Adding a NOT NULL column to a table that already has rows needs a `server_default` in the migration, or PostgreSQL rejects it.
- Commit `migrations/` together with the model change that caused it.
- Keep the schema at 2NF or better, with clear relationships. The diagram and column list are in `docs/database.md`.
- Delete your local `harambee.db` and run `db upgrade` again if your local database gets out of step with the migrations.

---

## 8. Authentication (JWT)

JWT (JSON Web Token) is a signed token the server gives you at login. The client sends it with every protected request, so the server knows who is calling without asking for the password again. We use Flask-JWT-Extended, already set up in `extensions.py` and `create_app()`.

- **Using it on a route:** use `@roles_required("organizer")` from `app/utils/decorators.py`. It checks the token and the role together, and it replaces `@jwt_required()`. Several roles: `@roles_required("organizer", "admin")`. `401` means not logged in (missing, invalid or expired token), `403` means the role is not allowed.
- **Reading the user:** `get_jwt_identity()` returns the user id as a string, and `get_jwt()["role"]` returns the role.
- **The token carries the role:** login creates it with `create_access_token(identity=str(user.id), additional_claims={"role": user.role})`. If the claim is missing, every role-protected route returns `403`.
- **Calling a protected route:** send the header `Authorization: Bearer <token>`.
- **Passwords** are hashed (`set_password` / `check_password` on the `User` model). Never store or return plain passwords or hashes. The minimum length is 8 characters.

### Registration and email verification (2-step signup)
1. `POST /api/auth/register` creates the user with `email_verified = false`, emails a signed, time-limited verification link, and returns a message (not a login token). Only `organizer` and `contributor` can self-register.
2. The user opens the link, which calls `GET /api/auth/verify-email/<token>` and sets `email_verified = true`. Expired or invalid links return `400`.
3. Admins are never created through registration. They are created in `seed.py`.

If sending the email fails, registration still succeeds and the response says `email_sent: false`, so a resend route is needed (see section 3).

---

## 9. API conventions

- All routes start with `/api`.
- JSON in, JSON out.
- **Pagination on every list endpoint:** `?page=1&per_page=10`. Return the items plus `page`, `per_page`, `total` and `pages`. `per_page` is capped at 100. Use the helper in `app/utils/pagination.py`.
- **Validation:** validate all input with Marshmallow schemas. Reject bad input with `422` and a clear message.
- **Errors:** one consistent shape, `{"error": "Short message", "details": {...}}` (`details` is optional), with the right status code (`400`, `401`, `403`, `404`, `409`, `422`). Global handlers in `app/utils/errors.py` make sure users never see an HTML error page or a stack trace.
- **Dates:** store as UTC and return ISO 8601 strings. The frontend formats them for people.
- **Money:** `Numeric(12, 2)`, never floats in the database.
- **Status codes:** `200` OK, `201` created, `204` deleted, `401` not logged in, `403` wrong role.
- **No real emails or uploads in tests.** Fake the SendGrid and Cloudinary calls.

### Endpoints
The full machine-readable list is `docs/openapi.yaml` (paste it into https://editor.swagger.io to browse it). Print the real list any time with `flask --app run routes`.

**Auth** (M6, M2)
| Method | Path | Access |
|--------|------|--------|
| POST | `/api/auth/register` | Public |
| GET | `/api/auth/verify-email/<token>` | Public |
| POST | `/api/auth/login` | Public |
| GET | `/api/auth/me` | Logged in |
| POST | `/api/auth/change-password` | Logged in |

**Pledges** (M4)
| Method | Path | Access |
|--------|------|--------|
| GET | `/api/pledges/campaign/<campaign_id>` | Public, paginated (anonymous pledges hide the contributor) |
| POST | `/api/pledges/campaign/<campaign_id>` | Contributor |
| GET | `/api/pledges/mine` | Logged in, paginated |
| GET | `/api/pledges/<id>` | The contributor, the campaign's organizer, or an admin |
| PATCH | `/api/pledges/<id>` | The contributor (pending pledges only) |
| DELETE | `/api/pledges/<id>` | The contributor or an admin (cancels a pending pledge) |
| POST | `/api/pledges/<id>/confirm` | The campaign's organizer or an admin |
| GET | `/api/pledges/campaign/<campaign_id>/manage` | The campaign's organizer or an admin, paginated |
| POST | `/api/pledges/<id>/remind` | The campaign's organizer |

**Campaigns** (M3) and **Admin** (M5): owners, add your final endpoints here in your next PR, using the same table format. Copy them from `flask --app run routes`.

---

## 10. Testing

We need at least **60% backend coverage, including endpoints**.

```bash
pytest                                            # run all tests
pytest --cov=app --cov-report=term-missing        # show coverage and the lines nobody tests
pytest --cov=app --cov-fail-under=60              # fail if coverage is below 60%
pytest tests/test_pledges.py -q                   # one file
```

- Tests live in `tests/`, one file per slice. **Write tests for your own routes in the same PR as the routes.**
- Shared setup is in `tests/conftest.py`: the `app`, `client`, `make_user(role=...)` and `auth_header(user)` fixtures. Use them instead of writing your own. It uses an in-memory database and test secrets, so tests never touch real data.
- Test failures as well as successes: missing fields, wrong role, missing token, duplicate email, unknown id.
- A skipped test is not a passing test. Do not use `skipif` to hide a missing dependency. Wait for it to be merged instead.
- Run `pytest` before opening every PR. CI (`.github/workflows/ci.yml`) runs it again on every PR and fails below 60% coverage.

---

## 11. Docs and deployment

- `docs/database.md`: ER diagram (renders on GitHub) and DBML for dbdiagram.io
- `docs/openapi.yaml`: API specification
- `docs/deployment.md`: deploying to Render with PostgreSQL, secrets, and the deploy hook used by CI
- `render.yaml`: Render blueprint

CI deploys only when code is pushed to `main`, after the tests pass. Nothing reaches production until the Scrum master merges `develop` into `main`.

---

## 12. Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: flask` or `ModuleNotFoundError` | The virtual environment is not active. Run `source venv/bin/activate`, then `pip install -r requirements.txt`. |
| `IndentationError: unexpected indent` | A line has extra leading spaces, often from copy-pasting. Top-level lines must start at the left edge. |
| `ImportError` mentioning a circular import | Create extensions in `extensions.py` without an app, attach them inside `create_app()`, and define relationships from one side only. |
| `ImportError: cannot import name ...` after pulling | A file you depend on changed. Run `pip install -r requirements.txt`, and check the import against the owner's file. |
| Port 5000 already in use | Stop the other process, or run with `--port 5001`. |
| `no such table` | Run `flask --app run db upgrade`. |
| `table ... already exists` during upgrade | Your local database was created outside migrations. Delete `harambee.db` (and `instance/harambee.db`) and run `db upgrade` again. |
| Migration fails with multiple heads | Two migrations branched from the same point. Tell the Scrum master. Do not edit old migrations. |
| `.env` values not loading | Check the file is named exactly `.env`, sits in the repo root, and `python-dotenv` is installed. |
| Frontend request blocked by CORS | Check that Flask-CORS is initialized and allows the frontend's address (`FRONTEND_URL`). |
| Merge conflict in `.gitignore` | Take `develop`'s version (`git checkout --theirs .gitignore` during the merge), then `git add .gitignore` and `git commit --no-edit`. |
| Postman says "Cannot send requests to reserved address" | Switch from the Cloud Agent to the Desktop Agent. |
