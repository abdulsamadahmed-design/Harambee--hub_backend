# Deployment guide (backend)

The brief asks for the frontend and the backend on different platforms. This guide deploys the API to Render with a PostgreSQL database. Put the React frontend on Netlify or Vercel.

SQLite is fine for local development but is wiped on most free hosts, so production needs PostgreSQL.

## 1. Changes to the code (small PRs, owners in brackets)

1. **`requirements.txt`** [Scrum master, one PR]: add two lines.
   - `gunicorn` is the production web server. Flask's built-in server is for development only.
   - `psycopg2-binary` lets SQLAlchemy talk to PostgreSQL.
2. **`app/config.py`** [M6]: some hosts give a database address starting with `postgres://`, but SQLAlchemy needs `postgresql://`. Convert it:
   ```python
   db_url = os.getenv("DATABASE_URL", "sqlite:///harambee.db")
   if db_url.startswith("postgres://"):
       db_url = db_url.replace("postgres://", "postgresql://", 1)
   SQLALCHEMY_DATABASE_URI = db_url
   ```
3. **CORS** [M6]: allow only the deployed frontend, not every website. Read `FRONTEND_URL` from the environment and pass it to Flask-CORS as the allowed origin.
4. **`run.py`** must expose a module-level variable called `app` (`app = create_app()`), because the start command is `gunicorn run:app`.
5. **A health route** at `/api/health` that returns a small JSON message, so you can check the deployed service is alive.

## 2. Create the services on Render

1. Create a **PostgreSQL** database on Render and copy its **Internal Database URL**.
2. Create a **Web Service** from the GitHub repo (or use `render.yaml` as a Blueprint).
   - Branch: `main`.
   - Build command: `pip install -r requirements.txt`
   - Start command: `flask --app run db upgrade && gunicorn run:app`
     It applies pending migrations, then starts the server.
3. Add environment variables in the dashboard:

   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | the PostgreSQL URL from step 1 |
   | `SECRET_KEY` | a long random string (the Blueprint can generate it) |
   | `JWT_SECRET_KEY` | a different long random string |
   | `FRONTEND_URL` | the deployed frontend address |
   | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` | once email is built |
   | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | once uploads are built |

   If the build fails on the Python version, set a `PYTHON_VERSION` variable to match the one you use locally.
4. Deploy, then open `https://<your-service>.onrender.com/api/health`.

Free instances go to sleep when idle, so the first request after a pause can take about a minute. Warm it up before a demo.

## 3. Automatic deploys from GitHub Actions

1. In the Render service settings, copy the **Deploy Hook** URL.
2. In GitHub go to **Settings > Secrets and variables > Actions > New repository secret**. Name it `DEPLOY_HOOK_URL` and paste the URL.
3. The `deploy` job in `.github/workflows/ci.yml` calls the hook after the tests pass on a push to `main`. If the secret is missing, the job skips itself and does not fail.

Nothing reaches production until the Scrum master merges `develop` into `main`.

## 4. Checklist before a demo

- [ ] `/api/health` answers on the deployed URL
- [ ] Register and login work from the deployed frontend (no CORS error in the browser console)
- [ ] The database has the tables (the start command ran `db upgrade`)
- [ ] An admin account exists (run `python seed.py` once, from the Render shell)
- [ ] No secrets in the repository, and `.env` is not committed
