# Phantom Internet Providers - WiFi Billing + FreeRADIUS

A complete WiFi ISP billing and authentication platform combining FreeRADIUS (AAA), PostgreSQL, FastAPI, and React.

## What This Does

- **Authentication**: FreeRADIUS validates WiFi users against a PostgreSQL database
- **Billing**: FastAPI backend manages subscriptions, customers, payments, and internet packages
- **Portal**: React frontend provides admin dashboard and customer portal
- **Accounting**: Real-time session tracking via RADIUS accounting tables

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ WiFi Access Points                                           │
│ (RADIUS clients)                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ RADIUS auth/accounting (UDP 1812/1813)
┌──────────────────────┴──────────────────────────────────────┐
│ FreeRADIUS Container (phantom-radius)                        │
│ - rlm_sql_postgresql: queries PostgreSQL for credentials    │
│ - rlm_expiration: rejects expired users                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ PostgreSQL Container (phantom-pg)                           │
│ - radcheck, radacct, radreply, etc. (FreeRADIUS schema)     │
│ - customers, subscriptions, payments, plans (billing)       │
│ - settings (configuration)                                  │
└──────────────────────────────────────────────────────────────┘
                       ▲
                       │ HTTP (port 8000)
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ FastAPI Backend (phantom-api or localhost:8000 on host)    │
│ - /api/auth - customer/admin login                          │
│ - /api/customers - customer management                      │
│ - /api/subscriptions - subscription CRUD                    │
│ - /api/payments - payment logging                           │
│ - /api/packages - internet plan management                  │
│ - /api/sessions - live RADIUS session tracking              │
│ - /api/settings - company settings                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (port 5173 dev / 80 prod)
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ React Frontend (Vite)                                        │
│ - LoginPage: customer/admin login                            │
│ - AdminDashboard: manage customers, packages, sessions       │
│ - AdminCustomers, AdminPackages, AdminSessions, AdminSettings
│ - CustomerDashboard: view subscription, download credentials │
│ - PaymentPage: record subscription extensions                │
└──────────────────────────────────────────────────────────────┘
```

## Project Layout

```
.
├── docker-compose.yml                 # Service orchestration
├── .env                               # Environment variables (defaults provided)
├── Dockerfile.freeradius              # FreeRADIUS image with PostgreSQL module
│
├── config/freeradius/
│   ├── clients.conf                   # NAS (access point) configuration
│   ├── mods-available/sql             # PostgreSQL module config
│   └── sites-available/default        # RADIUS server configuration
│
├── db/init/
│   ├── 01-freeradius-schema.sql       # Standard FreeRADIUS tables
│   ├── 02-billing-schema.sql          # Custom billing tables + functions
│   └── 03-settings.sql                # Default settings and test accounts
│
├── api_and_ui/api/
│   ├── Dockerfile                     # Python 3.12 + FastAPI image
│   ├── requirements.txt               # Python dependencies
│   └── app/
│       ├── main.py                    # FastAPI app + startup logic
│       ├── database.py                # SQLAlchemy setup
│       ├── models.py                  # ORM models (Customer, Subscription, etc.)
│       ├── schemas.py                 # Pydantic request/response schemas
│       ├── auth.py                    # JWT and password utilities
│       ├── default_packages.json      # Seed internet packages
│       ├── default_settings.json      # Seed company settings
│       └── routes/
│           ├── auth.py                # POST /api/auth/login
│           ├── customers.py           # /api/customers
│           ├── subscriptions.py       # /api/subscriptions
│           ├── payments.py            # /api/payments
│           ├── packages.py            # /api/packages
│           ├── sessions.py            # /api/sessions (live RADIUS sessions)
│           └── settings.py            # /api/settings
│
├── api_and_ui/ui/
│   ├── Dockerfile                     # Node 20 builder + Nginx prod image
│   ├── package.json                   # npm dependencies (React, Vite, Tailwind)
│   ├── nginx.conf                     # Production Nginx config
│   ├── vite.config.ts                 # Vite + React plugin + /api proxy
│   ├── tailwind.config.js             # Tailwind CSS configuration
│   └── src/
│       ├── main.tsx                   # React entrypoint
│       ├── App.tsx                    # Main router + layout
│       ├── index.css                  # Tailwind imports
│       ├── pages/
│       │   ├── LoginPage.tsx           # Email/password login
│       │   ├── CustomerDashboard.tsx   # Customer subscription view
│       │   ├── AdminDashboard.tsx      # Admin summary
│       │   ├── AdminCustomers.tsx      # Customer CRUD
│       │   ├── AdminPackages.tsx       # Internet package management
│       │   ├── AdminSessions.tsx       # Live RADIUS sessions
│       │   ├── AdminSettings.tsx       # Company settings
│       │   └── PaymentPage.tsx         # Record payment + extend subscription
│       ├── components/
│       │   ├── Layout.tsx              # Header + sidebar + main content
│       │   ├── PackageCard.tsx         # Internet package card display
│       │   ├── ConfirmModal.tsx        # Confirmation dialogs
│       │   ├── Toast.tsx               # Notifications
│       │   └── StatusIndicator.tsx     # Visual status badges
│       ├── contexts/
│       │   └── AuthContext.tsx         # JWT token + current user state
│       ├── services/
│       │   └── api.ts                  # Axios HTTP client
│       └── types/
│           └── index.ts                # TypeScript interfaces
│
└── tests/
    └── test_radius_auth.sh            # RADIUS authentication test script
```

## Ports Used

| Service | Port | Protocol | Container Name |
|---------|------|----------|----------------|
| PostgreSQL | `5432` | TCP | `phantom-pg` |
| FreeRADIUS Auth | `1812` | UDP | `phantom-radius` |
| FreeRADIUS Acct | `1813` | UDP | `phantom-radius` |
| FastAPI | `8000` | TCP | `phantom-api` |
| UI (dev Vite) | `5173` | TCP | localhost (host only) |
| UI (prod Nginx) | `80` | TCP | `phantom-ui` |

## Prerequisites

### For Running Containers (PostgreSQL + FreeRADIUS)
- **Docker** (20.10+)
- **Docker Compose** plugin

### For Running API on Host
- **Python 3.12+**
- **pip / venv**

### For Running UI on Host
- **Node.js 20+**
- **npm**

### Optional (For RADIUS testing)
- **radclient** - install with `apt install radius-utils` (Ubuntu/Debian) or `brew install radclient` (macOS)

---

## Security Note — Before You Start

> **⚠️ Hardcoded JWT secret fallback.** The API source (`api/app/config.py`) and
> `docker-compose.yml` both fall back to a well-known `JWT_SECRET` string when the
> environment variable is not set. Since the fallback value is visible in the
> repository source code, anyone who reads it can forge authentication tokens
> and impersonate any user — including admin.
>
> For local development this is acceptable. **For any shared, staging, or
> production deployment**, set a unique `JWT_SECRET` in `.env` before starting
> any services. The `.env` file now includes the `JWT_SECRET` variable —
> change its value to a long random string.

---

## Quick Start (Recommended for Development)

**Goal**: Run PostgreSQL + FreeRADIUS in containers, API + UI on host for fast iteration.

### Step 1: Start Database and RADIUS Server

```bash
cd /path/to/wifi_provider

# Start containers
docker compose up -d postgres freeradius

# Verify containers are running and healthy
docker compose ps

# Watch logs (Ctrl+C to exit)
docker compose logs -f postgres freeradius
```

Wait for `postgres` to be marked as `healthy` (5-15 seconds). The database initializes with:
- FreeRADIUS schema (radcheck, radacct, radreply, etc.)
- Billing schema (customers, subscriptions, payments, plans)
- Seed data: default settings, default internet packages, test accounts

### Step 2: Run API on Host

In a new terminal:

```bash
cd api_and_ui/api

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

Start the API server:

```bash
# Set environment variables for this terminal session
export DATABASE_URL="postgresql+psycopg://radius:radpass@localhost:5432/radius"
export JWT_SECRET="change-me-in-production"
export RADIUS_KEY="testing123"

# Start FastAPI with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify the API:
```bash
curl http://localhost:8000/
# Should return: {"name":"Phantom Internet Providers","version":"2.0.0","status":"online"}

curl http://localhost:8000/api/health
# Should return: {"status":"healthy","database":"connected"}
```

### Step 3: Run UI on Host

In a new terminal:

```bash
cd api_and_ui/ui

# Install npm dependencies
npm install

# Start Vite dev server on all network interfaces
npm run dev -- --host 0.0.0.0
```

You should see:
```
Local:    http://localhost:5173
Network:  http://192.168.x.x:5173
```

### Step 4: Access the Application

- **UI**: Open http://localhost:5173 (or your machine's IP)
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/api/health

---

## Default Credentials

### Admin Portal
- **Email**: `admin@phantomnet.co.ke`
- **Password**: `admin123`

### RADIUS Test Users (for authentication testing only, not in the UI)
- **Username**: `test_active`
  - **Password**: `testpass123`
  - **Status**: Active (should authenticate)
  
- **Username**: `test_expired`
  - **Password**: `expired123`
  - **Status**: Expired (RADIUS should reject)

---

## Database Schema Overview

### RADIUS Tables (FreeRADIUS)
| Table | Purpose |
|-------|---------|
| `radcheck` | User credentials (UserName, Attribute, Value) — e.g., Cleartext-Password, Expiration |
| `radreply` | Response attributes sent back to access points |
| `radusergroup` | Maps users to groups |
| `radacct` | Accounting records (sessions, bytes in/out, start/stop times) |
| `radpostauth` | Authentication attempt logs (success/failure) |

### Billing Tables (Custom)
| Table | Purpose |
|-------|---------|
| `customers` | Users: name, email, password_hash, is_admin flag |
| `plans` | Internet packages: name, price_cents, bandwidth limits, timeouts |
| `subscriptions` | Active subscriptions: customer + plan + period_start + period_end |
| `payments` | Payment ledger: subscription + amount + payment_method + timestamp |
| `settings` | Key-value config: company name, currency, defaults |

---

## Environment Variables

Set these in `.env` (project root) or export them before running services:

### PostgreSQL
```bash
POSTGRES_DB=radius                    # Database name
POSTGRES_USER=radius                  # Database user
POSTGRES_PASSWORD=radpass             # Database password
POSTGRES_HOST=postgres                # (Only for docker-compose, not for host)
```

### FreeRADIUS
```bash
RADIUS_KEY=testing123                 # Shared secret for NAS clients
RADIUS_PORT=1812                      # Auth port
RADIUS_ACCT_PORT=1813                 # Accounting port
```

### FastAPI (when running on host)
```bash
DATABASE_URL=postgresql+psycopg://radius:radpass@localhost:5432/radius
SYNC_DATABASE_URL=postgresql://radius:radpass@localhost:5432/radius
JWT_SECRET=change-me-in-production    # Secret key for JWT tokens
RADIUS_KEY=testing123                 # Must match FreeRADIUS secret
```

**⚠️ Production**: Change `JWT_SECRET`, `POSTGRES_PASSWORD`, and `RADIUS_KEY` before deploying.

---

## Testing

### Test 1: API Health Check
```bash
curl http://localhost:8000/api/health
```
Expected: `{"status":"healthy","database":"connected"}`

### Test 2: Admin Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@phantomnet.co.ke","password":"admin123"}'
```
Expected: JWT token in response

### Test 3: RADIUS Authentication (using radclient)

If `radclient` is installed on your host:

```bash
# Test active user (should accept)
echo "User-Name=test_active, User-Password=testpass123" \
  | radclient -x localhost:1812 auth testing123 2>&1 | grep "Access-Accept"

# Test expired user (should reject)
echo "User-Name=test_expired, User-Password=expired123" \
  | radclient -x localhost:1812 auth testing123 2>&1 | grep "Access-Reject"
```

### Test 4: RADIUS Test Suite (inside container)

```bash
# Copy test script into container
docker cp tests/test_radius_auth.sh phantom-radius:/tmp/test_radius_auth.sh

# Run test suite
docker compose exec freeradius bash /tmp/test_radius_auth.sh localhost

# Expected output:
# Test 1: Active user 'test_active' should AUTHENTICATE — ✓ PASS
# Test 2: Expired user 'test_expired' should be REJECTED — ✓ PASS
# Test 3: Wrong password should be REJECTED — ✓ PASS
# Test 4: Unknown user should be REJECTED — ✓ PASS
```

---

## Running Full Stack with Docker Compose

If you want all services in containers (useful for production-like testing):

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# Watch logs
docker compose logs -f

# Stop all
docker compose down

# Stop and remove database volume (destructive)
docker compose down -v
```

Services started:
- `postgres` (phantom-pg)
- `freeradius` (phantom-radius)
- `billing-api` (phantom-api)
- `frontend` (phantom-ui)

Access:
- UI: http://localhost:80
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## API Endpoints Summary

### Authentication
- `POST /api/auth/login` — Login with email/password or RADIUS credentials

### Customers (Admin only)
- `GET /api/customers` — List all customers
- `POST /api/customers` — Create customer
- `GET /api/customers/{id}` — Get customer details
- `PUT /api/customers/{id}` — Update customer
- `DELETE /api/customers/{id}` — Delete customer

### Subscriptions
- `GET /api/subscriptions` — List subscriptions (filtered by user)
- `POST /api/subscriptions` — Create subscription
- `GET /api/subscriptions/{id}` — Get subscription details
- `PUT /api/subscriptions/{id}` — Update subscription
- `DELETE /api/subscriptions/{id}` — Cancel subscription

### Payments
- `POST /api/payments` — Record payment and extend subscription
- `GET /api/payments` — List payments

### Internet Packages (Admin only)
- `GET /api/packages` — List all packages
- `POST /api/packages` — Create package
- `PUT /api/packages/{id}` — Update package
- `DELETE /api/packages/{id}` — Delete package

### Live Sessions
- `GET /api/sessions` — List active RADIUS sessions

### Settings (Admin only)
- `GET /api/settings` — Get company settings
- `PUT /api/settings` — Update settings

Full API documentation: http://localhost:8000/docs (interactive Swagger UI)

---

## UI Pages

### Public
- **Login** (`/login`) — Email/password login for customers and admins

### Customer
- **Dashboard** (`/dashboard`) — View active subscriptions, credentials, usage stats

### Admin (requires login)
- **Dashboard** (`/admin`) — Summary: active customers, revenue, sessions
- **Customers** (`/admin/customers`) — CRUD for customer accounts
- **Packages** (`/admin/packages`) — Manage internet packages
- **Sessions** (`/admin/sessions`) — View live RADIUS sessions
- **Settings** (`/admin/settings`) — Configure company name, currency, defaults
- **Payment** (`/admin/payment`) — Record customer payments

---

## Common Development Tasks

### Create a New Customer (via API)
```bash
curl -X POST http://localhost:8000/api/customers \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+254712345678"
  }'
```

### Create a Subscription for a Customer
```bash
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "plan_id": 1,
    "username": "john_doe",
    "password": "wifipass123"
  }'
```

### Record a Payment (extends subscription by 1 month)
```bash
curl -X POST http://localhost:8000/api/payments \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1,
    "amount_cents": 150000,
    "payment_method": "cash",
    "notes": "Monthly renewal"
  }'
```

### Get Active Sessions
```bash
curl http://localhost:8000/api/sessions \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

---

## Troubleshooting

### PostgreSQL Container Won't Start
```bash
# Check logs
docker compose logs postgres

# Ensure port 5432 is not in use
lsof -i :5432

# Remove volume and restart (destructive)
docker compose down -v
docker compose up -d postgres
```

### FreeRADIUS Auth Failures
```bash
# Check logs
docker compose logs freeradius

# Verify RADIUS_KEY in .env matches config/freeradius/clients.conf
grep secret config/freeradius/clients.conf

# Test connectivity
docker compose exec freeradius radtest test_active testpass123 localhost 0 testing123
```

### API Can't Connect to Database
```bash
# Ensure postgres is healthy
docker compose ps postgres

# Check DATABASE_URL format
echo $DATABASE_URL

# Verify credentials
psql postgresql://radius:radpass@localhost:5432/radius
```

### UI Can't Reach API
```bash
# Ensure API is running and accessible
curl http://localhost:8000/api/health

# Check Vite proxy in api_and_ui/ui/vite.config.ts
# Should have: /api proxy to http://localhost:8000

# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### JWT Token Expired
- Tokens are valid for 24 hours. Log in again to get a new token.
- The token is stored in browser localStorage under `auth_token`.

---

## Production Deployment Checklist

- [ ] Change `POSTGRES_PASSWORD` in `.env`
- [ ] Change `JWT_SECRET` in `.env`
- [ ] Change `RADIUS_KEY` in `.env`
- [ ] Disable `--reload` flag in FastAPI Dockerfile
- [ ] Set `CORS` origins in `api/app/main.py` to your domain(s)
- [ ] Use a reverse proxy (Nginx/Caddy) in front of the API
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Restrict RADIUS client IPs in `config/freeradius/clients.conf`
- [ ] Set up database backups
- [ ] Configure firewall rules (only expose 80, 443, 1812/udp, 1813/udp)
- [ ] Review PostgreSQL security settings
- [ ] Test payment workflows end-to-end
- [ ] Load test with multiple concurrent users

---

## Getting Help

### View Live Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f postgres
docker compose logs -f freeradius
docker compose logs -f billing-api
```

### API Interactive Docs
Open http://localhost:8000/docs and try endpoints directly.

### Database Queries (Direct)
```bash
psql postgresql://radius:radpass@localhost:5432/radius

# List customers
SELECT id, name, email, is_admin FROM customers;

# List active subscriptions
SELECT s.id, s.username, s.status, p.name, s.current_period_end
FROM subscriptions s
JOIN plans p ON p.id = s.plan_id
WHERE s.status = 'active';

# List recent sessions
SELECT UserName, AcctStartTime, AcctInputOctets, AcctOutputOctets
FROM radacct
WHERE AcctStopTime IS NULL
ORDER BY AcctStartTime DESC
LIMIT 10;
```

---

## Notes for New Developers

1. **Database is auto-initialized** on first `docker compose up`. Seeds include test users and packages.
2. **API auto-seeds** defaults on startup if tables are empty. See `api/app/main.py` startup function.
3. **Vite proxy** in dev mode forwards `/api/*` calls to the FastAPI backend. No CORS issues in dev.
4. **JWT tokens** are issued on login and stored in browser localStorage. Middleware verifies tokens on protected routes.
5. **RADIUS expiration** is handled by `rlm_expiration` module, which rejects users with past `Expiration` attribute in `radcheck`.
6. **Session tracking** is read from `radacct` table. No session table exists; RADIUS accounting is the source of truth.

---

## Production Notes

- Change all default passwords and secrets
- Disable debug and reload modes
- Serve UI via hardened reverse proxy with HTTPS
- Lock down database and RADIUS ports with firewall rules
- Set up automated backups for PostgreSQL
- Monitor RADIUS server logs for authentication anomalies
- Implement payment reconciliation workflows
- Set up alerts for failed subscriptions or payment processing
