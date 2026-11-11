# Harambee Hub - Backend API

REST API for Harambee Hub, a fundraising platform that replaces WhatsApp contribution lists. Organizers create campaigns, contributors pledge amounts, and the platform tracks who has actually paid. Roles: **organizer**, **contributor**, **admin**.

Built with Flask, SQLAlchemy, Flask-Migrate, Flask-JWT-Extended and Marshmallow. The React frontend lives in a separate repository and talks to this API over HTTP/JSON.

> Status: Phase 2 (backend) in progress. Update this README as features are built.

---

## 1. Rules for the whole team (read first)

### Never push or merge to `main`
- **Do not push to `main`. Do not merge into `main`.** Only the Scrum master merges `develop` into `main`, through a reviewed pull request, when `develop` is stable and demo-ready.
- **Do not push directly to `develop` either.** All work goes through a feature branch and a pull request (PR).
- Never use `git push --force` on a shared branch.

### Branch workflow (Gitflow)
| Branch | Purpose |
|--------|---------|
| `main` | Stable, demo-ready code only |
| `develop` | Integration branch where finished work is combined |
| `feature/<area>-<short-name>` | One task, for example `feature/auth-register` |

Steps for every task:
1. Make sure the task has a card on the Trello board. No card, no work.
2. `git checkout develop` then `git pull` - switch to `develop` and download the latest changes.
3. `git checkout -b feature/<area>-<short-name>` - create your own branch.
4. Work and commit in small steps (see commit messages below).
5. `git push -u origin feature/<area>-<short-name>` - upload your branch.
6. On GitHub, open a PR **into `develop`** (check the base branch, GitHub may default to `main`).
7. Get one review from a teammate who did not write the code. The Scrum master merges.
8. Pull `develop` into your branch every morning: `git checkout develop`, `git pull`, `git checkout <your-branch>`, `git merge develop`.

### Commit messages
Format: `type: short description` in the present tense, one idea per commit.

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

Examples: `feat: add user registration endpoint`, `fix: return 404 for missing campaign`, `test: cover pledge validation`.

### Pull request checklist
- [ ] App runs locally with no errors
- [ ] Tests pass (`pytest`) and new code has tests
- [ ] No secrets, `.env` files or `venv/` committed
- [ ] List endpoints are paginated
- [ ] Input is validated and errors return clear JSON messages
- [ ] PR description says what changed and how to test it

---

## 2. First-time setup

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
cp .env.example .env              # then open .env and fill in the values (see section 3)

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
- Add a new library: `pip install <package>`, then update the list with `pip freeze > requirements.txt`, and commit `requirements.txt` in the same PR so teammates get it.
- After pulling changes that touched `requirements.txt`, run `pip install -r requirements.txt` again.

---

## 3. Environment variables

Create `.env` from `.env.example`. **`.env` is ignored by Git and must never be committed.** If a secret is ever pushed, treat it as leaked and replace it.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | Key used to sign login tokens |
| `DATABASE_URL` | Database address, for example `sqlite:///harambee.db` for local development |
| `SENDGRID_API_KEY` | Sending emails (added when email is built) |
| `SENDGRID_FROM_EMAIL` | Verified sender address |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Image uploads (added when uploads are built) |

Generate a strong secret with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Use a different value for `SECRET_KEY` and `JWT_SECRET_KEY`. Teammates and production each get their own values.

---

## 4. Project structure

```
.
|-- app/
|   |-- __init__.py          # create_app() application factory
|   |-- config.py            # settings loaded from .env
|   |-- extensions.py        # db, migrate, jwt created here (no app yet)
|   |-- models/              # user.py, campaign.py, pledge.py
|   |-- routes/              # blueprints: auth, campaign, pledge, admin
|   |-- schemas/             # Marshmallow validation schemas
|   `-- utils/               # decorators.py, pagination, email, uploads
|-- migrations/              # created by flask db init, committed to Git
|-- tests/                   # pytest tests
|-- run.py                   # entry point: app = create_app()
|-- seed.py                  # sample data
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

Why `run.py` and not `app.py`: a file called `app.py` next to a folder called `app/` confuses Python's imports.

---

## 5. Database and migrations

Tables are defined as models in `app/models/`. Never edit the database by hand. Change the models, then create a migration.

```bash
flask --app run db init                 # once per project (creates migrations/)
flask --app run db migrate -m "add pledge table"   # generate a migration from model changes
flask --app run db upgrade              # apply migrations to your database
```

- Read the generated file in `migrations/versions/` before applying it.
- Commit `migrations/` with the model change that caused it.
- If two people create migrations at the same time, tell the Scrum master before merging.
- Keep the schema at 2NF or better, with clear relationships. Store the diagram in `docs/` (dbdiagram.io or similar).

---

## 6. Adding JWT authentication

JWT (JSON Web Token) is a signed token the server gives you at login. The client sends it with every protected request, so the server knows who is calling without asking for the password again. We use Flask-JWT-Extended.

### Setup (one time)
1. Install: `pip install flask-jwt-extended`, then `pip freeze > requirements.txt`.
2. Add `JWT_SECRET_KEY` to `.env` (see section 3).
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
5. Attach it inside `create_app()` in `app/__init__.py`: `jwt.init_app(app)`.

### Using it
- **Login:** after checking the password, create a token. Use a string for the identity and store the role as an extra claim:
  ```python
  from flask_jwt_extended import create_access_token
  token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
  ```
- **Protect a route:** add `@jwt_required()` under the route decorator. Inside the function, `get_jwt_identity()` returns the user id and `get_jwt()["role"]` returns the role.
- **Role checks:** put a reusable decorator in `app/utils/decorators.py` (for example one that allows only organizers or only admins) and return `403` when the role is wrong.
- **Calling a protected route:** send the header `Authorization: Bearer <token>`.
  ```bash
  curl -H "Authorization: Bearer <token>" http://127.0.0.1:5000/api/campaigns
  ```
- **Friendly errors:** use `@jwt.expired_token_loader`, `@jwt.invalid_token_loader` and `@jwt.unauthorized_loader` so a missing, invalid or expired token returns a clear JSON message with status `401`.

### Passwords
- Never store plain passwords. Hash them with `werkzeug.security.generate_password_hash` and check them with `check_password_hash` (or bcrypt).
- Never return password hashes in any response.

### 2-step signup (email token)
After registering, the user receives an email with a verification token and cannot log in until the email is verified. Store the token (or its expiry) and a verified flag, and decide with the team where they live.

---

## 7. API conventions

- All routes start with `/api`.
- JSON in, JSON out.
- **Pagination on every list endpoint:** `GET /api/campaigns?page=1&per_page=10`. Return the items plus `page`, `per_page`, `total` and `pages`. Cap `per_page` (for example at 100).
- **Validation:** validate all input with Marshmallow schemas. Reject bad input with `400` or `422` and a clear message.
- **Errors:** one consistent shape, for example `{"error": "Campaign not found"}`, with the right status code (`400`, `401`, `403`, `404`, `409`, `422`). Register global error handlers so users never see an HTML error page or a stack trace.
- **Dates:** store as UTC and return ISO 8601 strings. The frontend formats them for people.
- **Status codes:** `200` OK, `201` created, `204` deleted, `401` not logged in, `403` wrong role.

### Planned endpoints (draft, update as built)
| Method | Path | Access |
|--------|------|--------|
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| GET | `/api/campaigns` | Public, paginated |
| GET | `/api/campaigns/<id>` | Public |
| POST | `/api/campaigns` | Organizer |
| POST | `/api/campaigns/<id>/pledges` | Contributor |
| GET | `/api/pledges/mine` | Contributor |
| PATCH | `/api/pledges/<id>` | Organizer (mark paid) |
| GET | `/api/admin/users` | Admin |

---

## 8. Testing

We need at least **60% backend coverage, including endpoints**.

```bash
pytest                                            # run all tests
pytest --cov=app --cov-report=term-missing        # show coverage and missed lines
pytest --cov=app --cov-fail-under=60              # fail if coverage is below 60%
```

- Tests live in `tests/`. Use a separate test database (for example in-memory SQLite) so tests never touch real data.
- Test failures as well as successes: missing fields, wrong role, missing token, duplicate email, unknown id.
- Run `pytest` before opening every PR.

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: flask` or `ModuleNotFoundError` | The virtual environment is not active. Run `source venv/bin/activate`, then `pip install -r requirements.txt`. |
| `ImportError: cannot import name ...` (circular import) | Create extensions in `extensions.py` without an app, and attach them inside `create_app()`. |
| Port 5000 already in use | Stop the other process, or run with `--port 5001`. |
| `no such table` | Run `flask --app run db upgrade`. |
| Migration conflicts after a merge | Do not edit old migrations. Tell the Scrum master. |
| `.env` values not loading | Check the file is named exactly `.env`, sits in the repo root, and `python-dotenv` is installed. |
| Frontend request blocked by CORS | Check that Flask-CORS is initialized and allows the frontend's address. |

---

## 10. Still to add

- [ ] Frontend repository link
- [ ] Trello board link
- [ ] Database diagram in `docs/`
- [ ] Swagger / API documentation
- [ ] CI workflow (GitHub Actions: install, test, lint)
- [ ] Deployment instructions
- [ ] Team members and roles