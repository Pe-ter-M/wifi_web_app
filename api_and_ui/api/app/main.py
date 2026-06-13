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
    version="2.0.0",
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
    """Ensure default data exists (packages, admin user, settings)."""
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM settings")).scalar()
            if count == 0:
                defaults_path = os.path.join(os.path.dirname(__file__), "default_settings.json")
                with open(defaults_path) as f:
                    defs = json.load(f)
                conn.execute(
                    text("INSERT INTO settings (key, value, updated_at) VALUES (:k, :v, now())"),
                    [{"k": "company", "v": json.dumps(defs["company"])},
                     {"k": "defaults", "v": json.dumps(defs["defaults"])}],
                )

            count = conn.execute(text("SELECT COUNT(*) FROM plans")).scalar()
            if count == 0:
                pkgs_path = os.path.join(os.path.dirname(__file__), "default_packages.json")
                with open(pkgs_path) as f:
                    pkgs = json.load(f)
                for i, pkg in enumerate(pkgs):
                    conn.execute(
                        text("""INSERT INTO plans (name, description, price_cents, price_display,
                               bandwidth_up, bandwidth_down, session_timeout, idle_timeout,
                               is_active, sort_order) VALUES (:n, :d, :pc, :pd, :bu, :bd, :st, :it, :ia, :so)"""),
                        {"n": pkg["name"], "d": pkg["description"], "pc": pkg["price_cents"],
                         "pd": pkg["price_display"], "bu": pkg["bandwidth_up"], "bd": pkg["bandwidth_down"],
                         "st": pkg["session_timeout"], "it": pkg["idle_timeout"],
                         "ia": pkg["is_active"], "so": i},
                    )

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
    return {"name": "Phantom Internet Providers", "version": "2.0.0", "status": "online"}


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
        text("SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND current_period_end > now()")
    ).scalar()
    expired_subs = db.execute(
        text("SELECT COUNT(*) FROM subscriptions WHERE status = 'expired' OR current_period_end <= now()")
    ).scalar()
    live_sessions = db.execute(
        text("SELECT COUNT(*) FROM radacct WHERE AcctStopTime IS NULL")
    ).scalar()
    revenue_today = db.execute(
        text("SELECT COALESCE(SUM(amount_cents), 0) FROM payments WHERE paid_at::date = CURRENT_DATE")
    ).scalar()
    revenue_month = db.execute(
        text("SELECT COALESCE(SUM(amount_cents), 0) FROM payments WHERE date_trunc('month', paid_at) = date_trunc('month', CURRENT_DATE)")
    ).scalar()

    return {
        "total_customers": total_customers or 0,
        "active_subscriptions": active_subs or 0,
        "expired_subscriptions": expired_subs or 0,
        "live_sessions": live_sessions or 0,
        "revenue_today_cents": revenue_today or 0,
        "revenue_this_month_cents": revenue_month or 0,
    }


# Expose only selected API endpoints as MCP tools.
mcp = FastApiMCP(
    app,
    name="Phantom Internet Providers MCP",
    include_operations=["dashboard_stats", "list_customers", "get_customer"],
)
mcp.mount_http(mount_path="/api/mcp")
