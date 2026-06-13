"""Package/plan management (admin CRUD)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_admin, get_current_user
from app.database import get_db
from app.schemas import PlanCreate, PlanUpdate, PlanResponse

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("", response_model=list[PlanResponse])
async def list_packages(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),  # any authenticated user
):
    """List available packages. Admins see all, customers see active ones."""
    if user["is_admin"]:
        query = "SELECT * FROM plans ORDER BY sort_order, id"
    else:
        query = "SELECT * FROM plans WHERE is_active = true ORDER BY sort_order, id"
    result = db.execute(text(query))
    return [dict(row._mapping) for row in result]


@router.post("", response_model=PlanResponse, status_code=201)
async def create_package(
    body: PlanCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    result = db.execute(
        text("""
            INSERT INTO plans (name, description, price_cents, price_display,
                   bandwidth_up, bandwidth_down, session_timeout, idle_timeout,
                   is_active, sort_order)
            VALUES (:name, :desc, :price_cents, :price_display,
                    :bw_up, :bw_down, :session_to, :idle_to,
                    :active, :sort)
            RETURNING *
        """),
        {
            "name": body.name,
            "desc": body.description,
            "price_cents": body.price_cents,
            "price_display": body.price_display,
            "bw_up": body.bandwidth_up,
            "bw_down": body.bandwidth_down,
            "session_to": body.session_timeout,
            "idle_to": body.idle_timeout,
            "active": body.is_active,
            "sort": body.sort_order,
        },
    )
    db.commit()
    return dict(result.one()._mapping)


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_package(
    plan_id: int,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = plan_id

    result = db.execute(
        text(f"UPDATE plans SET {set_clause} WHERE id = :id RETURNING *"),
        updates,
    )
    db.commit()
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Package not found")
    return dict(row._mapping)


@router.delete("/{plan_id}", status_code=204)
async def delete_package(
    plan_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    # Check if any subscriptions use this plan
    count = db.execute(
        text("SELECT COUNT(*) FROM subscriptions WHERE plan_id = :pid"),
        {"pid": plan_id},
    )
    if count.scalar() > 0:
        raise HTTPException(400, "Cannot delete a plan with active subscriptions. Deactivate it instead.")
    db.execute(text("DELETE FROM plans WHERE id = :id"), {"id": plan_id})
    db.commit()
    return None
