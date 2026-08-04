# AI Predictor App

An AI-powered prediction app with a FastAPI backend and a React frontend. The backend is secured with authentication and rate limiting, and includes structured logging for observability.

## Quickstart

### Frontend

```bash
cd ai-predictor-app/frontend
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

### Backend (FastAPI)

Requirements:

- [uv](https://docs.astral.sh/uv/) — Python package/dependency manager
- [Docker](https://www.docker.com/) — required to run the Redis (rate limiting), Postgres (database), and optional Adminer (database UI) containers

```bash
cd your_project_name
uv sync
```

`uv` will automatically install the Python version required by the template (>=3.14), or use your existing Python installation if it already satisfies that requirement.

Start everything (Redis, Postgres, Adminer, and the API) with:

```bash
make up
```

Once running, the API and its interactive Swagger docs are available at:

[http://localhost:8000](http://localhost:8000)

### Generating the OpenAPI schema

To regenerate `openapi.json`:

```bash
python generate_openapi.py
```

### Database migrations

If you make changes to the database models, you can generate and apply a migration with Alembic:

```bash
alembic revision --autogenerate -m "create users table"
alembic upgrade head
```

## Features

- 🔐 **Authentication** — JWT access tokens and refresh tokens
- 🛡️ **Authorization** — route-level access control
- 🔑 **Hashed passwords** — passwords are never stored in plain text
- ✅ **Input validation** — schema-based request validation, with Alembic managing database migrations
- 🧱 **SQL injection prevention** — all queries go through SQLAlchemy's ORM/query builder
- 🚦 **Rate limiting** (via Redis)
- 📝 **Request/response logging**
- 🐘 **PostgreSQL** database
- 🛠️ Optional Adminer UI for inspecting the database
