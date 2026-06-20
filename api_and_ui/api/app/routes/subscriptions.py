"""Subscription management — create, list, status, my-credentials."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.schemas import SubscriptionCreate, SubscriptionResponse, SubscriptionStatusResponse

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if user["is_admin"]:
        result = db.execute(text("SELECT * FROM subscriptions ORDER BY id DESC"))
    else:
        result = db.execute(
            text("SELECT * FROM subscriptions WHERE customer_id = :cid ORDER BY id DESC"),
            {"cid": user["customer_id"]},
        )
    return [dict(row._mapping) for row in result]


@router.get("/my-credentials", response_model=list[dict])
async def my_credentials(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Customer's own subscriptions with PPPoE credentials."""
    result = db.execute(text("""
        SELECT s.id, s.status, s.current_period_start, s.current_period_end,
               s.cancelled_at, s.cancel_reason,
               p.name as plan_name, p.price, p.bandwidth_down, p.bandwidth_up,
               p.simultaneous_use as max_devices,
               pp.username, pp.password, pp.is_active as pppoe_active
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        LEFT JOIN pppoe_credentials pp ON pp.customer_id = s.customer_id
        WHERE s.customer_id = :cid
        ORDER BY s.id DESC
    """), {"cid": user["customer_id"]})

    now = datetime.datetime.now(datetime.timezone.utc)
    data = []
    for row in result.fetchall():
        end = row.current_period_end
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)

        is_active = row.status in ("active", "trial") and (end > now if end else False)

        dev_count = 0
        last_auth = None
        if row.username:
            dev_count = db.execute(
                text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
                {"u": row.username},
            ).scalar() or 0
            last_auth = db.execute(
                text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
                {"u": row.username},
            ).one_or_none()

        diff = end - now if end and end > now else datetime.timedelta(0)
        days = diff.days if diff.total_seconds() > 0 else 0

        data.append({
            "id": row.id,
            "username": row.username,
            "password": row.password,                    # Cleartext PPPoE password
            "status": row.status,
            "plan_name": row.plan_name,
            "price": row.price,
            "expires_at": end.isoformat() if end else None,
            "is_active": is_active,
            "days_remaining": days,
            "device_count": dev_count,
            "max_devices": row.max_devices or 1,
            "last_seen": last_auth.authdate.isoformat() if last_auth else None,
            "pppoe_active": row.pppoe_active,
        })
    return data


@router.post("", status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Create subscription for a customer. Customer must already have PPPoE credentials.
    Uses the SQL function create_subscription_from_payment with trial status."""
    
    # Check customer has PPPoE credentials
    pppoe = db.execute(
        text("SELECT * FROM pppoe_credentials WHERE customer_id = :cid AND is_active = true"),
        {"cid": body.customer_id},
    ).one_or_none()
    
    if not pppoe:
        raise HTTPException(400, "Customer does not have PPPoE credentials. Generate them first.")

    plan = db.execute(text("SELECT * FROM plans WHERE id = :pid"), {"pid": body.plan_id}).one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    # Default trial: 3 days
    trial_days = 3
    expires = now + datetime.timedelta(days=trial_days)

    sub_result = db.execute(
        text("""
            INSERT INTO subscriptions (customer_id, plan_id, status, current_period_start, current_period_end)
            VALUES (:cid, :pid, 'trial', :start, :end)
            RETURNING *
        """),
        {"cid": body.customer_id, "pid": body.plan_id, "start": now, "end": expires},
    )
    db.commit()
    
    sub = sub_result.one()
    
    return {
        "subscription_id": sub.id,
        "username": pppoe.username,
        "plan": plan.name,
        "price": plan.price,
        "status": "trial",
        "expires_at": expires.isoformat(),
        "trial_days": trial_days,
    }


@router.get("/{sub_id}/status", response_model=SubscriptionStatusResponse)
async def subscription_status(
    sub_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get subscription status with live data from RADIUS."""
    result = db.execute(text("""
        SELECT s.*, p.name as plan_name, p.price, p.simultaneous_use as max_devices,
               pp.username
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        LEFT JOIN pppoe_credentials pp ON pp.customer_id = s.customer_id
        WHERE s.id = :sid
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

    dev_count = 0
    last_auth = None
    if row.username:
        dev_count = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
            {"u": row.username},
        ).scalar() or 0
        last_auth = db.execute(
            text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
            {"u": row.username},
        ).one_or_none()

    return {
        "id": row.id,
        "username": row.username or "",
        "status": row.status,
        "plan_name": row.plan_name,
        "price": row.price or 0,
        "expires_at": period_end,
        "is_active": is_active,
        "days_remaining": max(0, days),
        "device_count": dev_count,
        "max_devices": row.max_devices or 1,
        "last_seen": last_auth.authdate if last_auth else None,
    }