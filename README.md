# Rise Back

Rise Back is a Flask fitness-progress game with workouts, missions, hydration,
weight tracking, boss battles, achievements, and the Aris mentor.

## Local setup

1. Create and activate a Python 3.12 virtual environment.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
4. Run `flask --app app run --debug`.

SQLite is used locally when `DATABASE_URL` is absent. Production should use
PostgreSQL.

## Deploy to Render

Push this directory to GitHub, then create a Render Blueprint and select the
repository. `render.yaml` provisions the web service, PostgreSQL database,
generated secret key, health check, and production start command.

The first deployment creates empty application tables automatically. Existing
installations with older database schemas should migrate or start with a fresh
production database because hydration and uniqueness constraints changed.

## Production checklist

- Confirm `/healthz` returns `{ "status": "ok" }`.
- Register a test account and complete the profile.
- Verify daily hydration resets on the next date.
- Keep `FLASK_DEBUG` disabled.
- Never commit `.env` or local SQLite files.
