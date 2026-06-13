"""SQLAlchemy ORM models for all tables."""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    Boolean, Float, CheckConstraint, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── FreeRADIUS standard tables ────────────────────────────────────

class RadCheck(Base):
    __tablename__ = "radcheck"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="==")
    Value = Column(Text, nullable=False)


class RadReply(Base):
    __tablename__ = "radreply"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="=")
    Value = Column(Text, nullable=False)


class RadUserGroup(Base):
    __tablename__ = "radusergroup"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    GroupName = Column(Text, nullable=False)
    priority = Column(Integer, default=0)


class RadAcct(Base):
    __tablename__ = "radacct"
    RadAcctId = Column(Integer, primary_key=True)
    UserName = Column(Text, index=True)
    AcctSessionId = Column(Text)
    NASIPAddress = Column(Text)
    AcctStartTime = Column(DateTime(timezone=True))
    AcctStopTime = Column(DateTime(timezone=True))
    AcctSessionTime = Column(Integer)
    AcctInputOctets = Column(Integer)
    AcctOutputOctets = Column(Integer)
    FramedIPAddress = Column(Text)
    CallingStationId = Column(Text)


class RadPostAuth(Base):
    __tablename__ = "radpostauth"
    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False, index=True)
    pass_field = Column("pass", Text)
    reply = Column(Text)
    authdate = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


# ── Custom billing tables ─────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True)
    phone = Column(Text)
    address = Column(Text)
    is_admin = Column(Boolean, default=False)
    password_hash = Column(Text)  # bcrypt hash for web portal login
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    subscriptions = relationship("Subscription", back_populates="customer")


class Plan(Base):
    """Internet package/plan (managed by admin)."""
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    price_cents = Column(Integer, nullable=False)
    price_display = Column(Float)                           # e.g., 1500.0 for display
    bandwidth_up = Column(Integer, default=8192)            # Kbps
    bandwidth_down = Column(Integer, default=8192)          # Kbps
    session_timeout = Column(Integer, default=86400)        # seconds
    idle_timeout = Column(Integer, default=600)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    username = Column(Text, unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)
    status = Column(Text, default="active")
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    customer = relationship("Customer", back_populates="subscriptions")
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','expired','cancelled','suspended')",
            name="ck_sub_status",
        ),
    )


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    amount_display = Column(Float)
    currency = Column(Text, default="KSH")
    payment_method = Column(Text, default="simulated")
    external_ref = Column(Text)
    paid_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    notes = Column(Text)


class Setting(Base):
    """Key-value settings table for company name, currency, etc."""
    __tablename__ = "settings"
    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
