"""Customer management — admin CRUD, detail view, PPPoE generation."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_admin, hash_password
from app.database import get_db
from app.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse], operation_id="list_customers")
async def list_customers(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
    search: str = Query(None),
):
    query = "SELECT * FROM customers WHERE is_admin = false"
    if search:
        query += " AND (name ILIKE :search OR email ILIKE :search OR phone ILIKE :search)"
    query += " ORDER BY id"
    result = db.execute(text(query), {"search": f"%{search}%" if search else ""})
    return [dict(row._mapping) for row in result]


@router.get("/{customer_id}", response_model=CustomerResponse, operation_id="get_customer")
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user["is_admin"] and user["customer_id"] != customer_id:
        raise HTTPException(403, "Access denied")
    result = db.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id})
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Customer not found")
    return dict(row._mapping)


@router.get("/{customer_id}/detail")
async def get_customer_detail(
    customer_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Full customer info + all subscriptions with live status."""
    from datetime import datetime, timezone
    cust = db.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id}).one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")

    subs = db.execute(text("""
        SELECT s.*, p.name as plan_name, p.price_display, p.bandwidth_down, p.bandwidth_up
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.customer_id = :cid ORDER BY s.id
    """), {"cid": customer_id}).fetchall()

    now = datetime.now(timezone.utc)
    sub_list = []
    for s in subs:
        end = s.current_period_end
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        is_active = s.status == "active" and (end > now if end else False)
        dev_count = db.execute(
            text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
            {"u": s.username},
        ).scalar() or 0
        last_auth = db.execute(
            text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
            {"u": s.username},
        ).one_or_none()

        sub_list.append({
            "id": s.id, "username": s.username, "password": s.password,
            "status": s.status, "plan_name": s.plan_name,
            "price_display": s.price_display,
            "bandwidth": f"{s.bandwidth_down // 1024} Mbps" if s.bandwidth_down else "-",
            "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
            "current_period_end": end.isoformat() if end else None,
            "is_active": is_active,
            "days_remaining": max(0, (end - now).days) if end else 0,
            "device_count": dev_count,
            "last_seen": last_auth.authdate.isoformat() if last_auth else None,
        })

    return {
        "customer": {
            "id": cust.id, "name": cust.name, "email": cust.email,
            "phone": cust.phone, "address": cust.address,
            "is_admin": cust.is_admin,
            "created_at": cust.created_at.isoformat() if cust.created_at else None,
        },
        "subscriptions": sub_list,
    }


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    if not body.name or not body.email or not body.phone:
        raise HTTPException(400, "Name, email, and phone are required")
    if not body.password or len(body.password) < 4:
        raise HTTPException(400, "Password is required and must be at least 4 characters")

    pw_hash = hash_password(body.password)
    result = db.execute(
        text("""
            INSERT INTO customers (name, email, phone, address, password_hash, is_admin)
            VALUES (:name, :email, :phone, :address, :pw_hash, :is_admin)
            RETURNING *
        """),
        {"name": body.name, "email": body.email, "phone": body.phone,
         "address": body.address, "pw_hash": pw_hash, "is_admin": body.is_admin or False},
    )
    db.commit()
    return dict(result.one()._mapping)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    body: CustomerCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    pw_hash = hash_password(body.password) if body.password else None
    result = db.execute(
        text("""
            UPDATE customers SET name=:n, email=:e, phone=:p, address=:a,
                password_hash=COALESCE(:pw, password_hash), is_admin=:ia, updated_at=now()
            WHERE id=:id RETURNING *
        """),
        {"id": customer_id, "n": body.name, "e": body.email, "p": body.phone,
         "a": body.address, "pw": pw_hash, "ia": body.is_admin or False},
    )
    db.commit()
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Customer not found")
    return dict(row._mapping)


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Delete customer and remove all FreeRADIUS entries."""
    usernames = db.execute(
        text("SELECT username FROM subscriptions WHERE customer_id = :cid"),
        {"cid": customer_id},
    ).fetchall()
    for row in usernames:
        u = row.username
        db.execute(text("DELETE FROM radcheck WHERE UserName = :u"), {"u": u})
        db.execute(text("DELETE FROM radreply WHERE UserName = :u"), {"u": u})
        db.execute(text("DELETE FROM radusergroup WHERE UserName = :u"), {"u": u})
    db.execute(text("DELETE FROM subscriptions WHERE customer_id = :cid"), {"cid": customer_id})
    db.execute(text("DELETE FROM customers WHERE id = :id"), {"id": customer_id})
    db.commit()
    return None


@router.post("/{customer_id}/generate-pppoe")
async def generate_pppoe(
    customer_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Generate one-time PPPoE credentials for a customer without a plan.
    Creates a subscription with a 1-hour trial session."""
    import secrets, string, datetime
    from sqlalchemy import text

    cust = db.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id}).one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")

    # Check if they already have an active subscription
    existing = db.execute(
        text("SELECT id FROM subscriptions WHERE customer_id = :cid AND status = 'active' AND current_period_end > now() LIMIT 1"),
        {"cid": customer_id},
    ).one_or_none()
    if existing:
        raise HTTPException(400, "Customer already has an active subscription")

    username = "user_" + "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    now = datetime.datetime.now(datetime.timezone.utc)
    expires = now + datetime.timedelta(hours=1)

    db.execute(
        text("""
            INSERT INTO subscriptions (customer_id, plan_id, username, password,
                   current_period_start, current_period_end, status)
            VALUES (:cid, (SELECT id FROM plans ORDER BY id LIMIT 1), :u, :pw, :start, :end, 'active')
        """),
        {"cid": customer_id, "u": username, "pw": password, "start": now, "end": expires},
    )
    db.execute(
        text("""
            INSERT INTO radcheck (UserName, Attribute, op, Value) VALUES
            (:u, 'Cleartext-Password', ':=', :pw),
            (:u, 'Expiration', ':=', :exp),
            (:u, 'Simultaneous-Use', ':=', '1')
        """),
        {"u": username, "pw": password, "exp": expires.strftime("%d %b %Y %H:%M:%S")},
    )
    db.execute(
        text("INSERT INTO radreply (UserName, Attribute, op, Value) VALUES (:u, 'Session-Timeout', ':=', '3600')"),
        {"u": username},
    )
    db.commit()

    return {"username": username, "password": password, "expires_at": expires.isoformat(), "trial": True}


@router.put("/{customer_id}/change-password", response_model=dict)
async def change_password(
    customer_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user["is_admin"] and user["customer_id"] != customer_id:
        raise HTTPException(403, "Access denied")
    new_password = body.get("password")
    if not new_password or len(new_password) < 4:
        raise HTTPException(400, "Password must be at least 4 characters")
    pw_hash = hash_password(new_password)
    db.execute(
        text("UPDATE customers SET password_hash = :pw, updated_at = now() WHERE id = :id"),
        {"pw": pw_hash, "id": customer_id},
    )
    db.commit()
    return {"message": "Password changed successfully"}
