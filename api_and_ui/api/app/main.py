"""Phantom Internet Providers — WiFi Billing API
FastAPI application serving customer portal and admin dashboard.
"""
import json
import os

from fastapi import FastAPI, Depends
from fastapi_mcp import FastApiMCP
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, engine
from app.models import Base
from app.auth import require_admin
from app.routes import auth, customers, packages, subscriptions, payments, settings, sessions

app = FastAPI(
    title="Phantom Internet Providers API",
    description="WiFi subscription billing system with FreeRADIUS backend",
    version="3.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(customers.router)
app.include_router(packages.router)
app.include_router(subscriptions.router)
app.include_router(payments.router)
app.include_router(settings.router)
app.include_router(sessions.router)


@app.on_event("startup")
def startup():
    """Ensure default data exists (plans, admin user, settings)."""
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            # Seed settings
            count = conn.execute(text("SELECT COUNT(*) FROM settings")).scalar()
            if count == 0:
                conn.execute(
                    text("INSERT INTO settings (key, value, updated_at) VALUES (:k, :v, now())"),
                    [
                        {"k": "company", "v": json.dumps({
                            "name": "Phantom Internet Providers",
                            "short_name": "PhantomNet",
                            "tagline": "Connect with confidence",
                            "currency": "KSH",
                            "currency_symbol": "KSh",
                            "support_email": "support@phantomnet.co.ke",
                            "support_phone": "+254 700 000000"
                        })},
                        {"k": "defaults", "v": json.dumps({
                            "max_devices": 1,
                            "session_timeout": 86400,
                            "idle_timeout": 600,
                            "trial_days": 3,
                            "subscription_days": 30
                        })},
                    ],
                )

            # Seed plans
            count = conn.execute(text("SELECT COUNT(*) FROM plans")).scalar()
            if count == 0:
                pkgs = [
                    {"name": "10Mbps", "group_name": "plan_10mbps", "description": "Basic - 10 Mbps",
                     "price": 1000.00, "bandwidth_up": 10240, "bandwidth_down": 10240,
                     "session_timeout": 86400, "idle_timeout": 600, "simultaneous_use": 1, "sort_order": 1},
                    {"name": "20Mbps", "group_name": "plan_20mbps", "description": "Standard - 20 Mbps",
                     "price": 2000.00, "bandwidth_up": 20480, "bandwidth_down": 20480,
                     "session_timeout": 86400, "idle_timeout": 600, "simultaneous_use": 1, "sort_order": 2},
                    {"name": "30Mbps", "group_name": "plan_30mbps", "description": "Premium - 30 Mbps",
                     "price": 3000.00, "bandwidth_up": 30720, "bandwidth_down": 30720,
                     "session_timeout": 86400, "idle_timeout": 600, "simultaneous_use": 2, "sort_order": 3},
                    {"name": "50Mbps", "group_name": "plan_50mbps", "description": "Ultimate - 50 Mbps",
                     "price": 5000.00, "bandwidth_up": 51200, "bandwidth_down": 51200,
                     "session_timeout": 86400, "idle_timeout": 600, "simultaneous_use": 2, "sort_order": 4},
                    {"name": "100Mbps", "group_name": "plan_100mbps", "description": "Business - 100 Mbps",
                     "price": 10000.00, "bandwidth_up": 102400, "bandwidth_down": 102400,
                     "session_timeout": 86400, "idle_timeout": 600, "simultaneous_use": 3, "sort_order": 5},
                ]
                for pkg in pkgs:
                    conn.execute(
                        text("""INSERT INTO plans (name, group_name, description, price,
                               bandwidth_up, bandwidth_down, session_timeout, idle_timeout,
                               simultaneous_use, is_active, sort_order)
                               VALUES (:n, :gn, :d, :p, :bu, :bd, :st, :it, :su, true, :so)"""),
                        {"n": pkg["name"], "gn": pkg["group_name"], "d": pkg["description"],
                         "p": pkg["price"], "bu": pkg["bandwidth_up"], "bd": pkg["bandwidth_down"],
                         "st": pkg["session_timeout"], "it": pkg["idle_timeout"],
                         "su": pkg["simultaneous_use"], "so": pkg["sort_order"]},
                    )

            # Seed admin user
            count = conn.execute(text("SELECT COUNT(*) FROM customers WHERE is_admin = true")).scalar()
            if count == 0:
                import bcrypt
                pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
                conn.execute(
                    text("INSERT INTO customers (name, email, password_hash, is_admin) VALUES ('Admin', 'admin@phantomnet.co.ke', :pw, true)"),
                    {"pw": pw},
                )
    except Exception as e:
        print(f"Startup seeding warning (already seeded): {e}")


@app.get("/")
def root():
    return {"name": "Phantom Internet Providers", "version": "3.0.0", "status": "online"}


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/dashboard/stats", operation_id="dashboard_stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    total_customers = db.execute(text("SELECT COUNT(*) FROM customers WHERE is_admin = false")).scalar()
    active_subs = db.execute(
        text("SELECT COUNT(*) FROM subscriptions WHERE status IN ('active', 'trial') AND current_period_end > now()")
    ).scalar()
    expired_subs = db.execute(
        text("SELECT COUNT(*) FROM subscriptions WHERE status = 'expired' OR current_period_end <= now()")
    ).scalar()
    live_sessions = db.execute(
        text("SELECT COUNT(*) FROM radacct WHERE AcctStopTime IS NULL")
    ).scalar()
    # ⚠️ CHANGED: amount_cents → amount (float)
    revenue_today = db.execute(
        text("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE paid_at::date = CURRENT_DATE")
    ).scalar()
    revenue_month = db.execute(
        text("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE date_trunc('month', paid_at) = date_trunc('month', CURRENT_DATE)")
    ).scalar()

    return {
        "total_customers": total_customers or 0,
        "active_subscriptions": active_subs or 0,
        "expired_subscriptions": expired_subs or 0,
        "live_sessions": live_sessions or 0,
        "revenue_today": float(revenue_today or 0),        # ⚠️ Changed key name
        "revenue_this_month": float(revenue_month or 0),    # ⚠️ Changed key name
    }


# Expose only selected API endpoints as MCP tools.
mcp = FastApiMCP(
    app,
    name="Phantom Internet Providers MCP",
    include_operations=["dashboard_stats", "list_customers", "get_customer"],
)
mcp.mount_http(mount_path="/api/mcp")