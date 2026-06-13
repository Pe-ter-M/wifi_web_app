"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_current_user, verify_password, hash_password, create_token
from app.database import get_db
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login using RADIUS credentials (username = radcheck username, password = Cleartext-Password)
    OR using customer table (for admins and portal-only users)."""
    result = db.execute(
        text("""
            SELECT c.id, c.name, c.email, c.is_admin, c.password_hash,
                   s.username as sub_username, s.password as sub_password, s.id as sub_id
            FROM customers c
            LEFT JOIN subscriptions s ON s.customer_id = c.id
            WHERE c.email = :username OR s.username = :username
            LIMIT 1
        """),
        {"username": body.username},
    )
    row = result.one_or_none()

    authenticated = False
    is_admin = False
    customer_id = None
    customer_name = "Unknown"

    if row:
        customer_id = row.id
        customer_name = row.name
        is_admin = row.is_admin or False

        # Try customer password_hash first
        if row.password_hash and await verify_password(body.password, row.password_hash):
            authenticated = True
        # Then try RADIUS password (plaintext check)
        elif row.sub_password and body.password == row.sub_password:
            authenticated = True

    # Also try direct radcheck lookup
    if not authenticated:
        result2 = db.execute(
            text("""
                SELECT c.id, c.name, c.is_admin
                FROM radcheck r
                JOIN subscriptions s ON s.username = r.UserName
                JOIN customers c ON c.id = s.customer_id
                WHERE r.UserName = :username
                  AND r.Attribute = 'Cleartext-Password'
                  AND r.Value = :password
                LIMIT 1
            """),
            {"username": body.username, "password": body.password},
        )
        row2 = result2.one_or_none()
        if row2:
            authenticated = True
            customer_id = row2.id
            customer_name = row2.name
            is_admin = row2.is_admin or False

    if not authenticated:
        raise HTTPException(401, "Invalid credentials")

    token = create_token(customer_id, body.username, is_admin, customer_name)

    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        is_admin=is_admin,
        customer_id=customer_id,
        customer_name=customer_name,
    )


@router.get("/me")
async def me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return current user info."""
    result = db.execute(
        text("SELECT id, name, email, phone, is_admin FROM customers WHERE id = :id"),
        {"id": user["customer_id"]},
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "User not found")
    return {
        "customer_id": row.id,
        "name": row.name,
        "email": row.email,
        "phone": row.phone,
        "is_admin": row.is_admin,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}
