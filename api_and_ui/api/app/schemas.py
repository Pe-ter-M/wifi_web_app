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
    password: Optional[str] = None            # web portal password
    is_admin: bool = False


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Plans / Packages ────────────────────────────────────────────────
class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_cents: int
    price_display: float
    bandwidth_up: int = 8192
    bandwidth_down: int = 8192
    session_timeout: int = 86400
    idle_timeout: int = 600
    is_active: bool = True
    sort_order: int = 0


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price_cents: Optional[int] = None
    price_display: Optional[float] = None
    bandwidth_up: Optional[int] = None
    bandwidth_down: Optional[int] = None
    session_timeout: Optional[int] = None
    idle_timeout: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlanResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price_cents: int
    price_display: float
    bandwidth_up: int
    bandwidth_down: int
    session_timeout: int
    idle_timeout: int
    is_active: bool
    sort_order: int

    model_config = {"from_attributes": True}


# ── Subscriptions ──────────────────────────────────────────────────
class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    username: Optional[str] = None             # auto-generated if blank
    password: Optional[str] = None             # auto-generated if blank


class SubscriptionResponse(BaseModel):
    id: int
    customer_id: int
    plan_id: int
    username: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionStatusResponse(BaseModel):
    username: str
    status: str                                # "active" | "expired" | "cancelled"
    plan_name: str
    expires_at: datetime
    is_active: bool                            # computed: now < expires_at AND status=active
    days_remaining: int                        # computed
    max_devices: int = 1
    current_device_count: int = 0
    last_seen: Optional[datetime] = None       # last auth attempt


# ── Payments ───────────────────────────────────────────────────────
class PaymentSimulate(BaseModel):
    subscription_id: int
    plan_id: Optional[int] = None              # if changing plan
    amount_cents: Optional[int] = None         # auto from plan if blank
    payment_method: str = "simulated"


class PaymentResponse(BaseModel):
    id: int
    subscription_id: int
    amount_cents: int
    amount_display: Optional[float] = None
    currency: str
    payment_method: str
    paid_at: datetime
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
    revenue_today_cents: int
    revenue_this_month_cents: int


# ── Generic ────────────────────────────────────────────────────────
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
