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
    """Login using web portal credentials (customers.password_hash) 
    OR PPPoE credentials (pppoe_credentials.password)."""
    
    # Try customer table first (web portal login)
    result = db.execute(
        text("""
            SELECT c.id, c.name, c.email, c.is_admin, c.password_hash
            FROM customers c
            WHERE c.email = :username
            LIMIT 1
        """),
        {"username": body.username},
    )
    row = result.one_or_none()

    authenticated = False
    is_admin = False
    customer_id = None
    customer_name = "Unknown"

    if row and row.password_hash:
        if await verify_password(body.password, row.password_hash):
            authenticated = True
            customer_id = row.id
            customer_name = row.name
            is_admin = row.is_admin or False

    # Try PPPoE credentials (RADIUS-style login)
    if not authenticated:
        result2 = db.execute(
            text("""
                SELECT c.id, c.name, c.is_admin
                FROM pppoe_credentials p
                JOIN customers c ON c.id = p.customer_id
                WHERE p.username = :username
                  AND p.password = :password
                  AND p.is_active = true
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