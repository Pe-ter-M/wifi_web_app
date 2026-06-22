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
    query = """
        SELECT c.*, 
               CASE WHEN p.id IS NOT NULL THEN true ELSE false END as has_pppoe,
               p.username as pppoe_username
        FROM customers c
        LEFT JOIN pppoe_credentials p ON p.customer_id = c.id
        WHERE c.is_admin = false
    """
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
    """Full customer info + subscriptions + PPPoE credentials."""
    from datetime import datetime, timezone

    cust = db.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id}).one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")

    # Get PPPoE credentials
    pppoe = db.execute(
    text("SELECT username, password, is_active FROM pppoe_credentials WHERE customer_id = :cid"),
    {"cid": customer_id}
).one_or_none()

    # Get subscriptions
    subs = db.execute(text("""
        SELECT s.*, p.name as plan_name, p.price, p.bandwidth_down, p.bandwidth_up,
               p.simultaneous_use as max_devices
        FROM subscriptions s
        JOIN plans p ON p.id = s.plan_id
        WHERE s.customer_id = :cid ORDER BY s.id DESC
    """), {"cid": customer_id}).fetchall()

    now = datetime.now(timezone.utc)
    sub_list = []
    for s in subs:
        end = s.current_period_end
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        is_active = s.status in ("active", "trial") and (end > now if end else False)

        # Get device count from radacct using PPPoE username
        dev_count = 0
        last_auth = None
        if pppoe:
            dev_count = db.execute(
                text("SELECT COUNT(*) FROM radacct WHERE UserName = :u AND AcctStopTime IS NULL"),
                {"u": pppoe.username},
            ).scalar() or 0
            last_auth = db.execute(
                text("SELECT authdate FROM radpostauth WHERE username = :u ORDER BY authdate DESC LIMIT 1"),
                {"u": pppoe.username},
            ).one_or_none()

        sub_list.append({
            "id": s.id,
            "username": pppoe.username if pppoe else None,
            "status": s.status,
            "plan_name": s.plan_name,
            "price": s.price,
            "bandwidth": f"{s.bandwidth_down // 1024} Mbps" if s.bandwidth_down else "-",
            "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
            "current_period_end": end.isoformat() if end else None,
            "is_active": is_active,
            "days_remaining": max(0, (end - now).days) if end else 0,
            "device_count": dev_count,
            "max_devices": s.max_devices or 1,
            "last_seen": last_auth.authdate.isoformat() if last_auth else None,
        })

    return {
        "customer": {
            "id": cust.id, "name": cust.name, "email": cust.email,
            "phone": cust.phone, "address": cust.address,
            "is_admin": cust.is_admin,
            "created_at": cust.created_at.isoformat() if cust.created_at else None,
        },
        "pppoe": {
            "username": pppoe.username if pppoe else None,
            "password": pppoe.password if pppoe else None,  
            "is_active": pppoe.is_active if pppoe else False,
            "has_credentials": pppoe is not None,
        },
        "subscriptions": sub_list,
    }


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    if not body.name or not body.email:
        raise HTTPException(400, "Name and email are required")
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
    """Delete customer using SQL function that cleans all related data."""
    # Check for active subscriptions first
    active = db.execute(
        text("SELECT COUNT(*) FROM subscriptions WHERE customer_id = :cid AND status IN ('active', 'trial')"),
        {"cid": customer_id},
    ).scalar()
    if active > 0:
        raise HTTPException(400, "Cannot delete customer with active subscriptions. Deactivate them first.")

    # Use the SQL function for complete cleanup
    result = db.execute(
        text("SELECT delete_customer(:cid)"),
        {"cid": customer_id},
    )
    db.commit()
    
    row = result.one_or_none()
    if row and row[0] and row[0].get("error"):
        raise HTTPException(404, row[0]["error"])
    
    return None


@router.post("/{customer_id}/generate-pppoe")
async def generate_pppoe(
    customer_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """Generate permanent PPPoE credentials for a customer.
    Uses the SQL function generate_pppoe_credentials."""
    
    cust = db.execute(text("SELECT * FROM customers WHERE id = :id"), {"id": customer_id}).one_or_none()
    if not cust:
        raise HTTPException(404, "Customer not found")

    result = db.execute(
        text("SELECT generate_pppoe_credentials(:cid)"),
        {"cid": customer_id},
    )
    db.commit()
    
    row = result.one_or_none()
    if row and row[0]:
        data = row[0]
        if data.get("error"):
            raise HTTPException(400, data["error"])
        return {
            "credential_id": data["credential_id"],
            "username": data["username"],
            "password": data["password"],
            "message": "Save these credentials — they will NOT be shown again"
        }
    
    raise HTTPException(500, "Failed to generate credentials")


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