"""Pydantic schemas for request/response validation."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ───────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_admin: bool = False
    customer_id: int | None = None
    customer_name: str | None = None


# ── Settings ───────────────────────────────────────────────────────
class CompanyInfo(BaseModel):
    name: str = "Phantom Internet Providers"
    short_name: str = "PhantomNet"
    tagline: str = "Connect with confidence"
    currency: str = "KSH"
    currency_symbol: str = "KSh"
    support_email: str = ""
    support_phone: str = ""


class SettingsResponse(BaseModel):
    company: CompanyInfo
    defaults: dict = {}


class SettingsUpdate(BaseModel):
    company: Optional[CompanyInfo] = None


# ── Customers ──────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
    is_admin: bool = False


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_admin: bool
    created_at: datetime
    has_pppoe: bool = False          
    pppoe_username: Optional[str] = None  

    model_config = {"from_attributes": True}


class CustomerDetailResponse(BaseModel):
    """Full customer detail with subscriptions."""
    customer: CustomerResponse
    subscriptions: list["SubscriptionDetailResponse"]


class SubscriptionDetailResponse(BaseModel):
    id: int
    username: str
    status: str
    plan_name: str
    price: float
    bandwidth: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    is_active: bool
    days_remaining: int
    device_count: int
    last_seen: Optional[datetime] = None


# ── Plans / Packages ────────────────────────────────────────────────
# ⚠️ BREAKING: price_cents/price_display removed, replaced with price (float)
# ⚠️ BREAKING: Added group_name, simultaneous_use fields
class PlanCreate(BaseModel):
    name: str
    group_name: Optional[str] = None            # Auto-generated if blank
    description: Optional[str] = None
    price: float                                # e.g., 1500.00
    bandwidth_up: int = 8192
    bandwidth_down: int = 8192
    session_timeout: int = 86400
    idle_timeout: int = 600
    simultaneous_use: int = 1
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    group_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None               # ⚠️ Changed from price_cents
    bandwidth_up: Optional[int] = None
    bandwidth_down: Optional[int] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    simultaneous_use: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    group_name: str
    description: Optional[str] = None
    price: float                                # ⚠️ Changed from price_cents
    bandwidth_up: int
    bandwidth_down: int
    session_timeout: int
    idle_timeout: int
    simultaneous_use: int
    is_active: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── PPPoE Credentials ──────────────────────────────────────────────
class PPPoECredentialResponse(BaseModel):
    id: int
    customer_id: int
    username: str
    password: str                              # Only shown once at creation
    is_active: bool
    created_at: datetime


class PPPoEGenerateResponse(BaseModel):
    credential_id: int
    username: str
    password: str                              # Show once - save it!


# ── Subscriptions ──────────────────────────────────────────────────
# ⚠️ BREAKING: No username/password in subscription - those are in pppoe_credentials
class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int


class SubscriptionResponse(BaseModel):
    id: int
    customer_id: int
    plan_id: int
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionStatusResponse(BaseModel):
    id: int
    username: str                              # From pppoe_credentials
    status: str
    plan_name: str
    price: float
    expires_at: datetime
    is_active: bool
    days_remaining: int
    device_count: int
    max_devices: int
    last_seen: Optional[datetime] = None


class MyCredentialsResponse(BaseModel):
    """Customer's own credentials and subscription info."""
    id: int
    username: str
    password: str                              # Cleartext PPPoE password
    status: str
    plan_name: str
    price: float
    expires_at: Optional[datetime] = None
    is_active: bool
    days_remaining: int
    device_count: int
    max_devices: int
    last_seen: Optional[datetime] = None


# ── Payments ───────────────────────────────────────────────────────
# ⚠️ BREAKING: amount_cents/amount_display → amount
class PaymentSimulate(BaseModel):
    subscription_id: int
    plan_id: Optional[int] = None
    amount: Optional[float] = None             # ⚠️ Changed from amount_cents
    payment_method: str = "simulated"


class PaymentResponse(BaseModel):
    id: int
    subscription_id: int
    amount: float                               # ⚠️ Changed
    currency: str
    payment_method: str
    external_ref: Optional[str] = None
    received_by: Optional[str] = None
    paid_at: datetime
    notes: Optional[str] = None
    new_expiry: Optional[datetime] = None
    username: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Sessions ───────────────────────────────────────────────────────
class LiveSessionResponse(BaseModel):
    radacct_id: int
    username: str
    nas_ip: str
    start_time: Optional[datetime] = None
    session_time: int = 0
    input_bytes: int = 0
    output_bytes: int = 0
    framed_ip: Optional[str] = None


class AuthLogResponse(BaseModel):
    id: int
    username: str
    reply: str
    authdate: datetime


# ── Dashboard ──────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_customers: int
    active_subscriptions: int
    expired_subscriptions: int
    live_sessions: int
    revenue_today: float                        # ⚠️ Changed from revenue_today_cents
    revenue_this_month: float                   # ⚠️ Changed from revenue_this_month_cents


# ── Generic ────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None