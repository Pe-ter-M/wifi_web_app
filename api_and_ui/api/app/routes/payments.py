"""Payment simulation — extends from 1h trial to 1 month, then same-date-next-month."""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.schemas import PaymentSimulate, PaymentResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])


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


@router.post("/simulate", response_model=PaymentResponse, status_code=201)
async def simulate_payment(
    body: PaymentSimulate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Simulate payment. First payment extends from NOW to 1 month (ends trial).
    Subsequent payments extend same-date-next-month."""
    sub = db.execute(
        text("SELECT * FROM subscriptions WHERE id = :sid"), {"sid": body.subscription_id}
    )
    sub_row = sub.one_or_none()
    if not sub_row:
        raise HTTPException(404, "Subscription not found")
    if not user["is_admin"] and user["customer_id"] != sub_row.customer_id:
        raise HTTPException(403, "Access denied")

    amount = body.amount_cents
    plan_id = body.plan_id or sub_row.plan_id

    if not amount:
        plan = db.execute(
            text("SELECT price_cents, price_display FROM plans WHERE id = :pid"),
            {"pid": plan_id},
        ).one_or_none()
        if not plan:
            raise HTTPException(404, "Plan not found")
        amount = plan.price_cents
        amount_display = plan.price_display
    else:
        amount_display = amount / 100.0

    now = datetime.datetime.now(datetime.timezone.utc)
    is_trial = sub_row.status == "trial"

    if is_trial:
        # First payment: extend from NOW to 1 month
        new_end = _same_date_next_month(now)
    else:
        # Subsequent payment: same-date-next-month from current expiry
        current_end = sub_row.current_period_end
        if current_end and current_end.tzinfo is None:
            current_end = current_end.replace(tzinfo=datetime.timezone.utc)
        if current_end and current_end > now:
            new_end = _same_date_next_month(current_end)
        else:
            new_end = _same_date_next_month(now)

    # Record payment (this counts as REAL revenue)
    pay_result = db.execute(
        text("""
            INSERT INTO payments (subscription_id, amount_cents, amount_display,
                  currency, payment_method, notes)
            VALUES (:sid, :amt, :amt_disp, 'KSH', 'payment',
                    'Plan: ' || COALESCE((SELECT name FROM plans WHERE id = :pid), ''))
            RETURNING *
        """),
        {"sid": body.subscription_id, "amt": amount, "amt_disp": amount_display, "pid": plan_id},
    )
    payment_row = pay_result.one()

    # Switch plan if changed
    if plan_id != sub_row.plan_id:
        db.execute(
            text("UPDATE subscriptions SET plan_id = :pid WHERE id = :sid"),
            {"pid": plan_id, "sid": body.subscription_id},
        )
        new_plan = db.execute(
            text("SELECT session_timeout FROM plans WHERE id = :pid"), {"pid": plan_id}
        ).one_or_none()
        if new_plan:
            db.execute(
                text("UPDATE radreply SET Value = :st WHERE UserName = :u AND Attribute = 'Session-Timeout'"),
                {"st": str(new_plan.session_timeout), "u": sub_row.username},
            )

    # Update subscription: status to active, extend expiry
    db.execute(
        text("UPDATE subscriptions SET current_period_end = :end, status = 'active', updated_at = now() WHERE id = :sid"),
        {"end": new_end, "sid": body.subscription_id},
    )

    # Update radcheck.Expiration
    db.execute(
        text("UPDATE radcheck SET Value = :val, op = ':=' WHERE UserName = :u AND Attribute = 'Expiration'"),
        {"val": new_end.strftime("%d %b %Y %H:%M:%S"), "u": sub_row.username},
    )

    db.commit()

    return PaymentResponse(
        id=payment_row.id,
        subscription_id=body.subscription_id,
        amount_cents=amount,
        amount_display=amount_display,
        currency="KSH",
        payment_method="payment",
        paid_at=payment_row.paid_at,
        new_expiry=new_end,
        username=sub_row.username,
    )


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
