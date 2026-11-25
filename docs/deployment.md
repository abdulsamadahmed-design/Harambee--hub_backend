# Backend Deployment Guide

The brief asks for the frontend and the backend on different platforms. This guide deploys the API to Render with a PostgreSQL database. Put the React frontend on Netlify or Vercel.

SQLite is fine for local development but is wiped on most free hosts, so production needs PostgreSQL.

## 1. Deployment requirements

The backend already includes:

- Gunicorn as the production web server.
- Psycopg 3 as the PostgreSQL driver.
- PostgreSQL URL conversion in `app/config.py`.
- CORS configuration through `FRONTEND_URL`.
- A module-level `app` in `run.py`.
- A health endpoint at `/api/health`.
- Database migrations managed by Flask-Migrate.

No additional deployment dependencies need to be installed.

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
   | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` | SendGrid credentials for email delivery |
   | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Cloudinary credentials for image uploads |
   | `ORGANIZER_EMAIL`, `ORGANIZER_PASSWORD` | Used when creating the initial organizer account |

   The Blueprint does not define the SendGrid, Cloudinary, or organizer variables. Add the required values manually in the Render dashboard. Keep real credentials out of the repository.

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
- [ ] The initial organizer account exists (set `ORGANIZER_EMAIL` and `ORGANIZER_PASSWORD`, then run `flask --app run seed-organizer` in the Render Shell)
- [ ] No secrets in the repository, and `.env` is not committed
