# Harambee Hub - Backend API

REST API for Harambee Hub, a fundraising platform that replaces WhatsApp contribution lists. Organizers create campaigns, contributors pledge amounts, and the platform tracks who has actually paid. Roles: **organizer**, **contributor**, **admin**.

Built with Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended and Marshmallow. The React frontend lives in a separate repository and talks to this API over HTTP/JSON.

Last updated: 11 Nov 2026. Update this file in the same PR as any change that affects setup, structure or ownership.

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
| `feature/<area>-<short-name>` | One task, for example `feature/auth-login` |

Steps for every task:
1. `git checkout develop` then `git pull` - switch to `develop` and download the latest changes.
2. `git checkout -b feature/<area>-<short-name>` - create your own branch from `develop`.
3. Work and commit in small steps (see commit messages below).
4. `git push -u origin feature/<area>-<short-name>` - upload your branch.
5. On GitHub, open a PR **into `develop`**. Check the base branch, because GitHub may default to `main`.
6. Get one review from a teammate who did not write the code (see the review ring in section 2). The Scrum master merges.
7. Bring in the latest work every morning: `git checkout develop`, `git pull`, `git checkout <your-branch>`, `git merge develop`.

### Commit messages
Format: `type: short description`, present tense, one idea per commit.
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.
Examples: `feat: add login endpoint`, `fix: return 404 for missing campaign`, `test: cover pledge validation`.

### Pull request checklist
- [ ] App runs locally with no errors
- [ ] Tests pass (`pytest`) and new code has tests
- [ ] No secrets, `.env` files or `venv/` committed
- [ ] List endpoints are paginated
- [ ] Input is validated and errors return clear JSON messages
- [ ] You only changed files you own (or agreed the change with the owner)
- [ ] PR description says what changed and how to test it

### Do not create `app.py`
The project has an `app/` folder. A file called `app.py` next to it clashes, because Python imports the folder and ignores the file. The entry point is `run.py`. Models go in `app/models/`, routes in `app/routes/`, schemas in `app/schemas/`. If you already pushed an `app.py`, move its contents into the right files and delete it before your PR is merged.

---

## 2. Team and file ownership

Everyone builds a complete slice (model, validation, routes, tests) and explains it at the Monday and Wednesday stand-ups. Everyone must understand the whole project, so read the other slices' PRs.

| Member | Name | Slice | Files you own |
|--------|------|-------|---------------|
| **M1 (Scrum master)** | | Validation for login, test setup, CI, docs, deployment | `app/schemas/auth_schema.py`, `app/utils/decorators.py`, `tests/conftest.py`, `.github/workflows/ci.yml`, `docs/` (database diagram, API docs), deployment files, `README.md`; fills test gaps until coverage reaches 60%; reviews and merges all PRs |
| **M2** | | Registration and email | `app/routes/registration_routes.py`, `app/schemas/registration_schema.py`, `app/utils/email.py` (SendGrid), `tests/test_registration.py` |
| **M3** | | Campaigns | `app/models/campaign.py`, `app/routes/campaign_routes.py`, `app/schemas/campaign_schema.py`, `app/utils/uploads.py` (Cloudinary), `tests/test_campaigns.py` |
| **M4** | | Pledges | `app/models/pledge.py`, `app/routes/pledge_routes.py`, `app/schemas/pledge_schema.py`, `tests/test_pledges.py` |
| **M5** | | Admin and shared tools | `app/routes/admin_routes.py`, `app/utils/pagination.py`, `seed.py`, `tests/test_admin.py`, `tests/test_pagination.py` |
| **M6** | | Foundation, users and login | `run.py`, `app/__init__.py`, `app/config.py`, `app/extensions.py`, `app/models/user.py`, `app/models/__init__.py`, `app/routes/auth_routes.py`, `app/utils/errors.py`, `.env.example` |

Fill in the Name column.

### Review ring
Every PR needs one reviewer who did not write it: M1 reviews M2, M2 reviews M3, M3 reviews M4, M4 reviews M5, M5 reviews M6, and M6 reviews M1. The Scrum master then does the final check and merge.

### Shared files, with rules
- `app/models/__init__.py`: each model owner adds **one import line** for their own model and nothing else. Merge that PR quickly.
- `requirements.txt`: if you install a library, add only that package's line. **Do not run `pip freeze > requirements.txt`** on a feature branch, because it rewrites the whole file and causes conflicts. Tell the Scrum master when you add one.
- `.env.example`: add only the variable names for your own feature (for example M2 adds the SendGrid ones, M3 adds the Cloudinary ones). Never put real values in it.
- Blueprint registration lives in `create_app()` (M6). Tell M6 the name of your blueprint, or add the one registration line in your PR.
- Need a change in a file you don't own? Ask the owner, or send a tiny separate PR.

### Names to agree on (confirm in the first meeting, then update here)
M6's login route depends on M1's files, so these names must be fixed early:
- Login validation: a schema class in `app/schemas/auth_schema.py` (proposed name: `LoginSchema`).
- Role check: a decorator in `app/utils/decorators.py` that takes the allowed roles (proposed name: `roles_required`, used like `@roles_required("organizer")`) and returns `403` when the role is wrong.
- Pagination: one helper in `app/utils/pagination.py` that every list endpoint calls.
- Email: one function in `app/utils/email.py` that sends a message, used by registration (M2) and pledge reminders (M4).

---

## 3. Order of work

1. **Day 1, everyone together:** agree the database schema on paper (tables, columns, relationships, status values). Models point at each other with foreign keys, so a late change breaks several people. Save the diagram in `docs/`.
2. **Day 1-2, first PRs:** M6 merges the foundation (app factory, `User`, extensions, error handlers) first. M5 builds the pagination helper. M1 sets up `conftest.py` once the factory exists. Everyone else designs their models and schemas on their branch but branches from `develop` after the foundation is merged.
3. **Then in parallel:** M2, M3 and M4 build their slices. M4 needs the `Campaign` model, so M3 merges the model early, ahead of the rest of the campaign routes. M4's reminder endpoint needs M2's email function.
4. **Last:** M5 finishes the seed data once all models exist, and M1 closes test and documentation gaps, CI and deployment.

---

## 4. First-time setup

Requirements: Python 3.10 or newer, Git. Windows users: use WSL or Git Bash.

```bash
# 1. Clone and enter the project (stay in the repo root for every command)
git clone <repo-url>
cd <repo-folder>

# 2. Switch to develop (if it does not exist yet, ask the Scrum master)
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

The API is now at `http://127.0.0.1:5000`. Check it with `http://127.0.0.1:5000/api/health`.

Every time you open a new terminal: `cd` into the repo root and run `source venv/bin/activate` again. If your prompt does not start with `(venv)`, the environment is not active.

### Installing dependencies
- Install everything the project needs: `pip install -r requirements.txt`
- After pulling changes that touched `requirements.txt`, run that command again.
- Adding a new library: `pip install <package>`, add its line to `requirements.txt` by hand (see the shared file rules in section 2), and mention it in your PR.

---

## 5. Environment variables

Create `.env` from `.env.example`. **`.env` is ignored by Git and must never be committed.** If a secret is ever pushed, treat it as leaked and replace it.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask secret key (also signs email verification tokens) |
| `JWT_SECRET_KEY` | Key used to sign login tokens |
| `DATABASE_URL` | Database address, for example `sqlite:///harambee.db` for local development |
| `SENDGRID_API_KEY` | Sending emails (added when email is built) |
| `SENDGRID_FROM_EMAIL` | Verified sender address |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Image uploads (added when uploads are built) |

Generate a strong secret with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Use different values for `SECRET_KEY` and `JWT_SECRET_KEY`. Each teammate and production get their own values.

---

## 6. Project structure

```
.
|-- app/
|   |-- __init__.py          # create_app() application factory
|   |-- config.py            # settings loaded from .env
|   |-- extensions.py        # db, migrate, jwt created here (no app yet)
|   |-- models/              # user.py, campaign.py, pledge.py
|   |-- routes/              # blueprints: auth, registration, campaign, pledge, admin
|   |-- schemas/             # Marshmallow validation schemas
|   `-- utils/               # decorators, errors, pagination, email, uploads
|-- migrations/              # created by flask db init, committed to Git
|-- tests/                   # pytest tests, one file per slice
|-- docs/                    # database diagram, API docs
|-- run.py                   # entry point: app = create_app()
|-- seed.py                  # sample data
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

---

## 7. Database and migrations

Tables are defined as models in `app/models/`. Never edit the database by hand. Change the models, then create a migration.

```bash
flask --app run db init                              # ONCE per project, by M6 only (creates migrations/)
flask --app run db migrate -m "add pledge table"     # generate a migration from model changes
flask --app run db upgrade                           # apply migrations to your database
```

- Everyone except M6 skips `db init`. After pulling, just run `db upgrade`.
- Pull `develop` **before** you run `db migrate`, and read the generated file in `migrations/versions/` before applying it.
- Two people generating migrations from the same starting point creates two "heads" and the database commands fail. Merge migration PRs one at a time, and tell the Scrum master if it happens. Never edit an old migration file.
- Commit `migrations/` together with the model change that caused it.
- Keep the schema at 2NF or better, with clear relationships.

---

## 8. Adding JWT authentication

JWT (JSON Web Token) is a signed token the server gives you at login. The client sends it with every protected request, so the server knows who is calling without asking for the password again. We use Flask-JWT-Extended. The wiring is done once by M6; everyone else only uses it.

### Setup (M6, one time)
1. `pip install flask-jwt-extended`, and add its line to `requirements.txt`.
2. Add `JWT_SECRET_KEY` to `.env`.
3. Create the manager in `app/extensions.py`:
   ```python
   from flask_jwt_extended import JWTManager
   jwt = JWTManager()
   ```
4. Load the settings in `app/config.py`:
   ```python
   import os
   from datetime import timedelta

   JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
   JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
   ```
5. Attach it inside `create_app()`: `jwt.init_app(app)`.

### Using it (everyone)
- **Protect a route:** add `@jwt_required()` under the route decorator. Inside the function, `get_jwt_identity()` returns the user id (a string) and `get_jwt()["role"]` returns the role.
- **Role checks:** use the decorator from `app/utils/decorators.py` instead of writing your own.
- **Login:** after checking the password, create a token with a string identity and the role as an extra claim:
  ```python
  from flask_jwt_extended import create_access_token
  token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
  ```
- **Calling a protected route:** send the header `Authorization: Bearer <token>`.
  ```bash
  curl -H "Authorization: Bearer <token>" http://127.0.0.1:5000/api/campaigns
  ```
- **Friendly errors:** `@jwt.expired_token_loader`, `@jwt.invalid_token_loader` and `@jwt.unauthorized_loader` make a missing, invalid or expired token return a clear JSON message with status `401`.

### Passwords
- Never store plain passwords. Hash them (`werkzeug.security.generate_password_hash`) and check with `check_password_hash`. The `User` model already does this through `set_password` and `check_password`.
- Never return password hashes in any response.

### 2-step signup (email token)
After registering, the user receives an email with a verification link and cannot log in until the email is verified. The `User` model has an `is_verified` flag and creates and checks a signed, time-limited token. M2 builds the routes that send and verify it.

---

## 9. API conventions

- All routes start with `/api`.
- JSON in, JSON out.
- **Pagination on every list endpoint:** `GET /api/campaigns?page=1&per_page=10`. Return the items plus `page`, `per_page`, `total` and `pages`. Cap `per_page` (for example at 100). Use the helper in `app/utils/pagination.py`.
- **Validation:** validate all input with Marshmallow schemas. Reject bad input with `400` or `422` and a clear message.
- **Errors:** one consistent shape, for example `{"error": "Campaign not found"}`, with the right status code (`400`, `401`, `403`, `404`, `409`, `422`). Global handlers in `app/utils/errors.py` make sure users never see an HTML error page or a stack trace.
- **Dates:** store as UTC and return ISO 8601 strings. The frontend formats them for people.
- **Status codes:** `200` OK, `201` created, `204` deleted, `401` not logged in, `403` wrong role.

### Planned endpoints (draft, update as built)
| Method | Path | Access | Owner |
|--------|------|--------|-------|
| POST | `/api/auth/register` | Public | M2 |
| GET | `/api/auth/verify/<token>` | Public | M2 |
| POST | `/api/auth/login` | Public | M6 |
| GET | `/api/auth/me` | Logged in | M6 |
| GET | `/api/campaigns` | Public, paginated | M3 |
| GET | `/api/campaigns/<id>` | Public | M3 |
| POST | `/api/campaigns` | Organizer | M3 |
| POST | `/api/campaigns/<id>/pledges` | Contributor | M4 |
| GET | `/api/pledges/mine` | Contributor | M4 |
| PATCH | `/api/pledges/<id>` | Organizer (mark paid) | M4 |
| GET | `/api/admin/users` | Admin, paginated | M5 |

---

## 10. Testing

We need at least **60% backend coverage, including endpoints**.

```bash
pytest                                            # run all tests
pytest --cov=app --cov-report=term-missing        # show coverage and missed lines
pytest --cov=app --cov-fail-under=60              # fail if coverage is below 60%
```

- Tests live in `tests/`, one file per slice. **Write tests for your own routes in the same PR as the routes.** The Scrum master fills remaining gaps, not whole slices.
- Shared setup is in `tests/conftest.py`. Tests use a separate test database (for example in-memory SQLite) and never touch real data.
- Test failures as well as successes: missing fields, wrong role, missing token, duplicate email, unknown id.
- Run `pytest` before opening every PR. CI runs it again on every PR.

---

## 11. Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: flask` or `ModuleNotFoundError` | The virtual environment is not active. Run `source venv/bin/activate`, then `pip install -r requirements.txt`. |
| `IndentationError: unexpected indent` | A line has extra leading spaces, often from copy-pasting. Top-level lines must start at the left edge. |
| `ImportError` mentioning a circular import | Create extensions in `extensions.py` without an app, attach them inside `create_app()`, and define relationships from one side only (for example in `campaign.py`). |
| Port 5000 already in use | Stop the other process, or run with `--port 5001`. |
| `no such table` | Run `flask --app run db upgrade`. |
| Migration fails with multiple heads | Two migrations branched from the same point. Tell the Scrum master. Do not edit old migrations. |
| `.env` values not loading | Check the file is named exactly `.env`, sits in the repo root, and `python-dotenv` is installed. |
| Frontend request blocked by CORS | Check that Flask-CORS is initialized and allows the frontend's address. |

---

## 12. Progress and still to add

- [x] Repository, `.gitignore`, README and virtual environment set up
- [ ] Database schema agreed and diagram saved in `docs/`
- [ ] Foundation merged: app factory, config, extensions, `User` model, error handlers (M6)
- [ ] Login and `/me` routes (M6), login schema and role decorator (M1)
- [ ] Registration and email verification (M2)
- [ ] Campaigns with image upload (M3)
- [ ] Pledges, mark as paid, reminders (M4)
- [ ] Pagination helper, admin routes, seed data (M5)
- [ ] Test setup and CI (M1), coverage at 60% or more
- [ ] Swagger / API documentation
- [ ] Deployment instructions
- [ ] Frontend repository link and Trello board link
