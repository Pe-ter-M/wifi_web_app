# Phantom Internet Providers - WiFi Billing + FreeRADIUS

This project is a WiFi ISP billing platform that combines:

- FreeRADIUS for AAA (authentication, authorization, accounting)
- PostgreSQL for RADIUS and billing data
- FastAPI backend for admin/customer operations
- React + Vite frontend for admin and customer portals

It supports:

- customer management
- package/plan management
- subscription lifecycle
- payment logging and subscription extension
- live session and auth log visibility from RADIUS tables

## Architecture

- `postgres` container hosts both FreeRADIUS tables (`radcheck`, `radacct`, etc.) and billing tables (`customers`, `subscriptions`, `payments`, etc.)
- `freeradius` container authenticates against PostgreSQL via `rlm_sql_postgresql`
- FastAPI reads/writes billing + RADIUS tables and seeds defaults at startup
- React UI calls the API through `/api` (Vite proxy in dev)

## Repository Layout

- `docker-compose.yml` - service orchestration
- `Dockerfile.freeradius` - FreeRADIUS image setup
- `config/freeradius/` - clients, sql module config, default site config
- `db/init/` - PostgreSQL bootstrap SQL scripts
- `api_and_ui/api/` - FastAPI backend
- `api_and_ui/ui/` - React frontend
- `tests/test_radius_auth.sh` - RADIUS auth validation script

## Ports Used

- PostgreSQL: `5432/tcp`
- FreeRADIUS auth: `1812/udp`
- FreeRADIUS accounting: `1813/udp`
- API: `8000/tcp`
- UI dev server: `5173/tcp`
- UI container (nginx): `80/tcp`

## Prerequisites (Host / Hardware Device)

Install on your hardware device (Linux):

- Docker + Docker Compose plugin
- Python 3.12+
- Node.js 20+
- npm

Optional but useful:

- `radclient` (for direct RADIUS testing from host)

## Environment

The project root `.env` file already defines defaults:

- `POSTGRES_DB=radius`
- `POSTGRES_USER=radius`
- `POSTGRES_PASSWORD=radpass`
- `RADIUS_KEY=testing123`

You can keep these for local/lab use, but change them for production.

## 1) Start PostgreSQL + FreeRADIUS Containers

From project root:

```bash
docker compose up -d postgres freeradius
```

Check status:

```bash
docker compose ps
docker compose logs -f postgres freeradius
```

What happens on first start:

- `db/init/01-freeradius-schema.sql` creates standard RADIUS tables
- `db/init/02-billing-schema.sql` creates billing tables/functions and seed test users
- `db/init/03-settings.sql` seeds default company/default settings

Stop only these services:

```bash
docker compose stop postgres freeradius
```

Stop and remove containers/network:

```bash
docker compose down
```

Remove DB volume too (destructive):

```bash
docker compose down -v
```

## 2) Run API on Hardware Device (Host)

Run the backend directly on your device while PostgreSQL + FreeRADIUS stay in containers.

```bash
cd api_and_ui/api
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install "psycopg[binary]"
```

Set runtime environment (same terminal):

```bash
export DATABASE_URL="postgresql+psycopg://radius:radpass@localhost:5432/radius"
export JWT_SECRET="change-me-in-production"
export RADIUS_KEY="testing123"
```

Start API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify:

- `http://<device-ip>:8000/`
- `http://<device-ip>:8000/api/health`
- `http://<device-ip>:8000/docs`

## 3) Run UI on Hardware Device (Host)

In a new terminal:

```bash
cd api_and_ui/ui
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Open from another device on the same network:

- `http://<device-ip>:5173`

Vite is configured to proxy `/api` to `http://localhost:8000`, so with API running on the same hardware device this works out of the box.

## 4) Default Login and Seed Accounts

Admin portal default:

- username: `admin@phantomnet.co.ke`
- password: `admin123`

RADIUS test users created from SQL seed:

- active user: `test_active` / `testpass123`
- expired user: `test_expired` / `expired123` (should be rejected)

## 5) Test FreeRADIUS Authentication

Run the included script from inside the FreeRADIUS container:

```bash
docker cp tests/test_radius_auth.sh phantom-radius:/tmp/test_radius_auth.sh
docker compose exec freeradius bash /tmp/test_radius_auth.sh localhost
```

Expected:

- `test_active` authenticates (`Access-Accept`)
- `test_expired` rejected (`Access-Reject`)
- wrong password rejected
- unknown user rejected

## 6) Optional: Run Full Stack with Docker Compose

`docker-compose.yml` currently references:

- `./api_and_ui/api`
- `./api_and_ui/ui`

In this repository, actual paths are:

- `./api_and_ui/api`
- `./api_and_ui/ui`

If you want to run `billing-api` and `frontend` through Docker Compose, update those two build contexts first, then run:

```bash
docker compose up -d
```

## Troubleshooting

- API cannot connect to DB:
	- ensure `postgres` is up: `docker compose ps`
	- verify `DATABASE_URL` uses `localhost:5432` when API runs on host
- FreeRADIUS auth fails:
	- check secret in `config/freeradius/clients.conf` matches `RADIUS_KEY`
	- inspect logs: `docker compose logs -f freeradius`
- UI cannot call API:
	- ensure API is running on port `8000`
	- ensure UI was started with Vite (`npm run dev`)

## Production Notes

- change all default passwords/secrets
- disable debug/reload in API
- serve UI via hardened reverse proxy
- lock down DB and RADIUS ports with firewall rules
