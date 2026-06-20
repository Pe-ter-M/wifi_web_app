"""Payment processing — uses SQL function for subscription extension."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.schemas import PaymentSimulate, PaymentResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/simulate", response_model=PaymentResponse, status_code=201)
async def simulate_payment(
    body: PaymentSimulate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Process payment using SQL function create_subscription_from_payment.
    Handles: trial→active conversion, monthly renewal, plan changes."""
    
    # Verify subscription exists and belongs to user
    sub = db.execute(
        text("SELECT s.*, pp.username FROM subscriptions LEFT JOIN pppoe_credentials pp ON pp.customer_id = s.customer_id WHERE s.id = :sid"),
        {"sid": body.subscription_id}
    ).one_or_none()
    
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if not user["is_admin"] and user["customer_id"] != sub.customer_id:
        raise HTTPException(403, "Access denied")

    # Get plan name
    plan_id = body.plan_id or sub.plan_id
    plan = db.execute(text("SELECT name, price FROM plans WHERE id = :pid"), {"pid": plan_id}).one_or_none()
    if not plan:
        raise HTTPException(404, "Plan not found")

    amount = body.amount or plan.price

    # Use SQL function for complete payment processing
    result = db.execute(
        text("""
            SELECT create_subscription_from_payment(
                :cid, :plan_name, :amount, :method, :ref, :received_by
            )
        """),
        {
            "cid": sub.customer_id,
            "plan_name": plan.name,
            "amount": amount,
            "method": body.payment_method,
            "ref": f"api_sim_{datetime.datetime.utcnow().timestamp()}",
            "received_by": user["name"] if user["is_admin"] else "self_service",
        },
    )
    db.commit()
    
    row = result.one_or_none()
    if row and row[0]:
        data = row[0]
        if data.get("error"):
            raise HTTPException(400, data["error"])
        
        return PaymentResponse(
            id=data.get("payment_id", 0),
            subscription_id=body.subscription_id,
            amount=amount,
            currency="KSH",
            payment_method=body.payment_method,
            paid_at=datetime.datetime.now(datetime.timezone.utc),
            new_expiry=data.get("new_expiry"),
            username=data.get("username"),
        )
    
    raise HTTPException(500, "Payment processing failed")


@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    subscription_id: int | None = None,
):
    if user["is_admin"]:
        if subscription_id:
            result = db.execute(
                text("SELECT * FROM payments WHERE subscription_id = :sid ORDER BY paid_at DESC"),
                {"sid": subscription_id},
            )
        else:
            result = db.execute(text("SELECT * FROM payments ORDER BY paid_at DESC"))
    else:
        result = db.execute(
            text("""
                SELECT p.* FROM payments p
                JOIN subscriptions s ON s.id = p.subscription_id
                WHERE s.customer_id = :cid ORDER BY p.paid_at DESC
            """),
            {"cid": user["customer_id"]},
        )
    return [dict(row._mapping) for row in result]