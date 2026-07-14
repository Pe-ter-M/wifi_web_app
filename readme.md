# Phantom Internet Providers - WiFi Billing + FreeRADIUS

A complete WiFi ISP billing and authentication platform combining FreeRADIUS (AAA), PostgreSQL, FastAPI, and React.

## What This Does

- **Authentication**: FreeRADIUS validates WiFi users against PostgreSQL via group-based policies
- **Billing**: FastAPI backend manages customers, PPPoE credentials, subscriptions, payments, and plans
- **Portal**: React frontend provides admin dashboard and customer self-service portal
- **Accounting**: Real-time session tracking via RADIUS accounting tables
- **PPPoE**: Customers get permanent PPPoE credentials that never change, even when switching plans
- **RADIUS Group Sync**: Plan changes auto-sync to FreeRADIUS group tables (radgroupcheck/radgroupreply)

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
│ - RADIUS group policies (radgroupcheck/radgroupreply)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│ PostgreSQL Container (phantom-pg)                           │
│ - radcheck, radacct, radreply, etc. (FreeRADIUS schema)     │
│ - radgroupcheck, radgroupreply, radusergroup (group policy) │
│ - pppoe_credentials (permanent customer credentials)        │
│ - customers, subscriptions, payments, plans (billing)       │
│ - password_history, audit_logs (security)                   │
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
│ - /api/payments - payment processing via SQL function       │
│ - /api/packages - internet plan management + RADIUS sync   │
│ - /api/sessions - live RADIUS sessions and auth log        │
│ - /api/settings - company settings                          │
│ - /api/mcp - MCP tool endpoint (AI assistant integration)  │
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
│       ├── main.py                    # FastAPI app + startup seeding + MCP mount
│       ├── database.py                # SQLAlchemy setup
│       ├── models.py                  # ORM models (Customer, Plan, Subscription, PPPoECredential, etc.)
│       ├── schemas.py                 # Pydantic request/response schemas
│       ├── auth.py                    # JWT + bcrypt utilities
│       ├── config.py                  # App config (JWT_SECRET, DB URL, defaults)
│       ├── default_settings.json      # Seed company settings
│       └── routes/
│           ├── auth.py                # POST /api/auth/login, GET /me, POST /logout
│           ├── customers.py           # /api/customers CRUD + PPPoE generation
│           ├── subscriptions.py       # /api/subscriptions + /my-credentials
│           ├── payments.py            # POST /payments/simulate, GET /payments
│           ├── packages.py            # /api/packages (plans CRUD + RADIUS sync)
│           ├── sessions.py            # /api/sessions/live, /auth-log
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
- FreeRADIUS schema (radcheck, radacct, radreply, radgroupcheck, radgroupreply, nas, etc.)
- Billing schema (customers, plans, pppoe_credentials, subscriptions, payments, etc.)
- SQL functions (generate_pppoe_credentials, sync_plan_to_radius, create_subscription_from_payment, etc.)
- Seed data: default settings, default internet plans, admin user

When the API starts, it also auto-seeds plans and the admin account if the tables are empty.

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
# Should return: {"name":"Phantom Internet Providers","version":"3.0.0","status":"online"}

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

### Default Plans (auto-seeded on first startup)
| Plan | Price | Bandwidth | Simultaneous Use |
|------|-------|-----------|-----------------|
| 10Mbps | KSh 1,000 | 10 Mbps / 10 Mbps | 1 device |
| 20Mbps | KSh 2,000 | 20 Mbps / 20 Mbps | 1 device |
| 30Mbps | KSh 3,000 | 30 Mbps / 30 Mbps | 2 devices |
| 50Mbps | KSh 5,000 | 50 Mbps / 50 Mbps | 2 devices |
| 100Mbps | KSh 10,000 | 100 Mbps / 100 Mbps | 3 devices |

RADIUS test users (`test_active`, `test_expired`) are no longer seeded. Use the API to create
customers, generate PPPoE credentials, and create subscriptions to test RADIUS auth.

---

## Database Schema Overview

### RADIUS Tables (FreeRADIUS)
| Table | Purpose |
|-------|---------|
| `radcheck` | User credentials (UserName, Attribute, Value) — e.g., Cleartext-Password, Expiration |
| `radreply` | Response attributes sent back to access points |
| `radusergroup` | Maps users to RADIUS groups |
| `radgroupcheck` | Group-level check attributes (restrictions like Simultaneous-Use) |
| `radgroupreply` | Group-level reply attributes (policies like bandwidth, session timeout) |
| `radacct` | Accounting records (sessions, bytes in/out, start/stop times) |
| `radpostauth` | Authentication attempt logs (success/failure) |
| `nas` | Network Access Servers (routers/APs registered for RADIUS) |

### Billing Tables (Custom)
| Table | Purpose |
|-------|---------|
| `customers` | User accounts: name, email, password_hash, is_admin |
| `plans` | Internet packages: name, group_name, price (float), bandwidth limits, simultaneous_use |
| `pppoe_credentials` | Permanent PPPoE credentials — assigned once, never change |
| `subscriptions` | Links customer + plan; carries status (trial/active/expired) and period |
| `payments` | Payment ledger: subscription + amount (float) + payment_method + paid_at |
| `password_history` | Audit trail for web portal password changes |
| `audit_logs` | General billing audit trail (table changes, admin actions) |
| `settings` | Key-value config: company info, defaults (trial_days, max_devices) |

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

### Test 3: Create Customer + PPPoE + Subscription (end-to-end)

```bash
# 1. Login as admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@phantomnet.co.ke","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Create a customer
CUST=$(curl -s -X POST http://localhost:8000/api/customers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"test1234"}')
echo "$CUST" | python3 -m json.tool

# 3. Generate PPPoE credentials (permanent — never change)
PPPOE=$(curl -s -X POST http://localhost:8000/api/customers/2/generate-pppoe \
  -H "Authorization: Bearer $TOKEN")
echo "$PPPOE"  # Save the username and password — they won't be shown again

# 4. Create a subscription (trial)
curl -s -X POST http://localhost:8000/api/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"customer_id":2,"plan_id":1}' | python3 -m json.tool
```

### Test 4: RADIUS Authentication (using radclient)

If `radclient` is installed, test with the PPPoE credentials generated above:

```bash
# Replace user_a1b2c3d4 and e5f6g7h8i9j0 with the actual PPPoE credentials
echo "User-Name=user_a1b2c3d4, User-Password=e5f6g7h8i9j0" \
  | radclient -x localhost:1812 auth testing123 2>&1 | grep "Access-Accept"
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
- `POST /api/auth/login` — Login with email/password or PPPoE credentials (returns JWT + cookie)
- `GET /api/auth/me` — Get current user info
- `POST /api/auth/logout` — Clear auth cookie

### Customers (Admin CRUD)
- `GET /api/customers` — List customers (supports `?search=` filter)
- `POST /api/customers` — Create customer
- `GET /api/customers/{id}` — Get customer details
- `PUT /api/customers/{id}` — Update customer
- `DELETE /api/customers/{id}` — Delete customer (checks no active subs)
- `GET /api/customers/{id}/detail` — Full detail: customer + subs + PPPoE credentials
- `POST /api/customers/{id}/generate-pppoe` — Generate permanent PPPoE credentials
- `PUT /api/customers/{id}/change-password` — Change web portal password

### Subscriptions
- `GET /api/subscriptions` — List subscriptions (filtered by user role)
- `POST /api/subscriptions` — Create subscription (customer must have PPPoE credentials)
- `GET /api/subscriptions/{id}/status` — Subscription status with device count
- `GET /api/subscriptions/my-credentials` — Customer's own subs with PPPoE credentials

### Payments
- `POST /api/payments/simulate` — Record payment and extend subscription (uses SQL function)
- `GET /api/payments` — List payments (filtered by user role)

### Internet Packages (Admin CRUD)
- `GET /api/packages` — List plans (admins see all, customers see active)
- `POST /api/packages` — Create plan (auto-generates group_name, syncs to RADIUS)
- `PUT /api/packages/{id}` — Update plan (auto-syncs to RADIUS group tables)
- `DELETE /api/packages/{id}` — Delete plan (blocked if subscriptions exist)

### Live Sessions
- `GET /api/sessions/live` — Active RADIUS sessions (acct stopped is null)
- `GET /api/sessions/auth-log` — Recent RADIUS auth attempts

### Dashboard
- `GET /api/dashboard/stats` — Admin summary: customers, active/expired subs, live sessions, revenue

### Settings (Admin)
- `GET /api/settings` — Get company settings (public)
- `PUT /api/settings` — Update company settings

### MCP (AI Assistant)
- `GET /api/mcp` — MCP HTTP endpoint for LLM tool access (exposes dashboard_stats, list_customers, get_customer)

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
    "phone": "+254712345678",
    "password": "temp1234"
  }'
```

### Generate PPPoE Credentials (required before creating a subscription)
```bash
curl -X POST http://localhost:8000/api/customers/1/generate-pppoe \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
# Returns: {"credential_id": 1, "username": "user_a1b2c3d4", "password": "e5f6g7h8i9j0"}
# These credentials are permanent and never change.
```

### Create a Subscription for a Customer
```bash
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "plan_id": 1
  }'
# Note: No username/password — those come from PPPoE credentials
```

### Record a Payment (extends subscription by 1 month)
```bash
curl -X POST http://localhost:8000/api/payments/simulate \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": 1,
    "amount": 1000,
    "payment_method": "cash",
    "notes": "Monthly renewal"
  }'
```

### Get Active Sessions
```bash
curl http://localhost:8000/api/sessions/live \
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

# Test connectivity with a customer's PPPoE credentials
docker compose exec freeradius radtest user_a1b2c3d4 e5f6g7h8i9j0 localhost 0 testing123
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

1. **Database is auto-initialized** on first `docker compose up`. Seeds include settings, plans, and admin user.
2. **API auto-seeds** on startup if tables are empty. See `api/app/main.py` startup function (seeds settings, plans, admin).
3. **PPPoE credentials are permanent** — each customer gets one set of PPPoE credentials that never change. Credentials are generated via `POST /api/customers/{id}/generate-pppoe` (uses a SQL function). Subscriptions no longer carry a username/password — they reference the plan and the customer's PPPoE credentials.
4. **RADIUS group sync is automatic** — PostgreSQL triggers `sync_plan_to_radius()` on plan INSERT/UPDATE and `trg_sync_subscription_to_radius()` on subscription changes. Plan bandwidth, session timeout, and simultaneous-use limits are pushed to `radgroupcheck`/`radgroupreply`.
5. **Payments use a SQL function** — `create_subscription_from_payment()` handles trial→active, monthly renewal, and plan changes as a single atomic operation.
6. **Vite proxy** in dev mode forwards `/api/*` calls to the FastAPI backend. No CORS issues in dev.
7. **JWT tokens** are issued on login and stored in browser localStorage + HTTP-only cookie. Middleware verifies tokens on protected routes.
8. **Login supports both methods** — email/password (web portal) OR PPPoE username/password (RADIUS-style direct login to the web app).
9. **MCP endpoint** at `/api/mcp` exposes the API as Model Context Protocol tools. AI assistants can call `dashboard_stats`, `list_customers`, and `get_customer` through this endpoint.
10. **RADIUS expiration** is handled by `rlm_expiration` module, which rejects users with past `Expiration` attribute in `radcheck`. Expiration is synced from the subscription's `current_period_end`.
11. **Session tracking** is read from `radacct` table. No session table exists; RADIUS accounting is the source of truth.
12. **Secret configuration** — `JWT_SECRET` has a hardcoded fallback in `config.py` and `docker-compose.yml`. Change it in `.env` for any non-local deployment.

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
