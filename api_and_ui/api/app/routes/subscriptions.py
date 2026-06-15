"""Subscription management — create with 1h trial, list, status, my-credentials."""
import datetime
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.schemas import SubscriptionCreate, SubscriptionResponse, SubscriptionStatusResponse

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


def _gen_username():
    return "user_" + "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))


def _gen_password(length=10):
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


def _same_date_next_month(dt: datetime.datetime) -> datetime.datetime:
    month = dt.month + 1
    year = dt.year
    if month > 12:
        month = 1
        year += 1
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, max_day)
    return dt.replace(year=year, month=month, day=day)


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user["is_admin"]:
        result = db.execute(text("SELECT * FROM subscriptions ORDER BY id"))
    else:
        result = db.execute(
            text("SELECT * FROM subscriptions WHERE customer_id = :cid ORDER BY id"),
            {"cid": user["customer_id"]},
        )
    return [dict(row._mapping) for row in result]


@router.get("/my-credentials", response_model=list[dict])
async def my_credentials(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = db.execute(text("""
        SELECT s.id, s.username, s.password, s.status, s.current_period_end,
               p.name as plan_name, p.price_display, p.price_cents
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.customer_id = :cid ORDER BY s.id
    """), {"cid": user["customer_id"]})

    now = datetime.datetime.now(datetime.timezone.utc)
    data = []
    for row in result.fetchall():
        end = row.current_period_end
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)

        is_trial = row.status == "trial"
        is_active = (row.status in ("active", "trial")) and (end > now if end else False)

        dev_count = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
            {"u": row.username},
        ).scalar() or 0
        last_seen = db.execute(
            text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
            {"u": row.username},
        ).one_or_none()

        diff = end - now if end and end > now else datetime.timedelta(0)
        total_secs = int(diff.total_seconds())
        days, rem = divmod(total_secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)

        data.append({
            "id": row.id, "username": row.username, "password": row.password,
            "status": row.status, "plan_name": row.plan_name,
            "price_display": row.price_display,
            "expires_at": end.isoformat() if end else None,
            "is_active": is_active,
            "is_trial": is_trial,
            "days_remaining": days,
            "hours_remaining": hours,
            "mins_remaining": mins,
            "secs_remaining": secs,
            "total_seconds_remaining": total_secs,
            "device_count": dev_count, "max_devices": 1,
            "last_seen": last_seen.authdate.isoformat() if last_seen else None,
        })
    return data


@router.post("", status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Create subscription with 1-hour free trial.
    Admin sees the initial 1-hour expiry. Customer pays to extend to 1 month."""
    username = body.username or _gen_username()
    password = body.password or _gen_password()

    if db.execute(text("SELECT 1 FROM radcheck WHERE UserName = :u"), {"u": username}).one_or_none():
        raise HTTPException(400, f"Username '{username}' already exists")

    plan = db.execute(text("SELECT * FROM plans WHERE id = :pid"), {"pid": body.plan_id}).one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(hours=1)  # 1-hour free trial

    sub_result = db.execute(
        text("""
            INSERT INTO subscriptions (customer_id, plan_id, username, password,
                current_period_start, current_period_end, status)
            VALUES (:cid, :pid, :u, :pw, :start, :end, 'trial')
            RETURNING *
        """),
        {"cid": body.customer_id, "pid": body.plan_id, "u": username,
        "pw": password, "start": now, "end": expires},
    )

    db.execute(
        text("INSERT INTO radcheck (UserName, Attribute, op, Value) VALUES "
            "(:u, 'Cleartext-Password', ':=', :pw), "
            "(:u, 'Expiration', ':=', :exp), "
            "(:u, 'Simultaneous-Use', ':=', '1')"),
        {"u": username, "pw": password, "exp": expires.strftime("%d %b %Y %H:%M:%S")},
    )
    db.execute(
        text("INSERT INTO radusergroup (UserName, GroupName, priority) VALUES (:u, :g, 1)"),
        {"u": username, "g": plan.name},
    )
    db.execute(
        text("INSERT INTO radreply (UserName, Attribute, op, Value) VALUES (:u, 'Session-Timeout', ':=', :t)"),
        {"u": username, "t": str(plan.session_timeout)},
    )

    db.commit()
    return {
        "subscription_id": sub_result.one().id, "username": username, "password": password,
        "plan": plan.name, "price_display": plan.price_display,
        "expires_at": expires.isoformat(), "trial": True,
        "trial_hours": 1,
    }


@router.get("/{sub_id}/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    sub_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = db.execute(text("""
        SELECT s.*, p.name as plan_name FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id WHERE s.id = :sid
    """), {"sid": sub_id})
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Subscription not found")
    if not user["is_admin"] and user["customer_id"] != row.customer_id:
        raise HTTPException(403, "Access denied")

    now = datetime.datetime.now(datetime.timezone.utc)
    period_end = row.current_period_end
    if period_end and period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=datetime.timezone.utc)
    is_active = row.status in ("active", "trial") and (period_end > now if period_end else False)
    days = (period_end - now).days if period_end else 0

    dev_count = db.execute(
        text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
        {"u": row.username},
    ).scalar() or 0
    last_auth = db.execute(
        text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
        {"u": row.username},
    ).one_or_none()

    return {
        "username": row.username, "status": row.status, "plan_name": row.plan_name,
        "expires_at": period_end, "is_active": is_active,
        "days_remaining": max(0, days), "max_devices": 1,
        "current_device_count": dev_count,
        "last_seen": last_auth.authdate if last_auth else None,
    }
