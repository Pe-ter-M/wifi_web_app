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
    """User authentication credentials and check attributes."""
    __tablename__ = "radcheck"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="==")
    Value = Column(Text, nullable=False)


class RadReply(Base):
    """User-specific reply attributes and overrides."""
    __tablename__ = "radreply"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="=")
    Value = Column(Text, nullable=False)


class RadUserGroup(Base):
    """User-to-group membership mapping."""
    __tablename__ = "radusergroup"
    id = Column(Integer, primary_key=True)
    UserName = Column(Text, nullable=False, index=True)
    GroupName = Column(Text, nullable=False)
    priority = Column(Integer, default=0)


class RadAcct(Base):
    """Session accounting and real-time usage tracking."""
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
    """Post-authentication logging and audit trail."""
    __tablename__ = "radpostauth"
    id = Column(Integer, primary_key=True)
    username = Column(Text, nullable=False, index=True)
    pass_field = Column("pass", Text)
    reply = Column(Text)
    authdate = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)


class RadGroupCheck(Base):
    """Group-level check attributes (restrictions)."""
    __tablename__ = "radgroupcheck"
    id = Column(Integer, primary_key=True)
    GroupName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="==")
    Value = Column(Text, nullable=False)


class RadGroupReply(Base):
    """Group-level reply attributes (policies)."""
    __tablename__ = "radgroupreply"
    id = Column(Integer, primary_key=True)
    GroupName = Column(Text, nullable=False, index=True)
    Attribute = Column(Text, nullable=False)
    op = Column(String(2), default="=")
    Value = Column(Text, nullable=False)


class Nas(Base):
    """Network Access Server (MikroTik routers, switches, etc.)."""
    __tablename__ = "nas"
    id = Column(Integer, primary_key=True)
    nasname = Column(Text, nullable=False)
    shortname = Column(Text)
    type = Column(Text, default="other")
    ports = Column(Integer)
    secret = Column(Text, nullable=False)
    server = Column(Text)
    community = Column(Text)
    description = Column(Text)


# ── Custom billing tables ─────────────────────────────────────────

class Customer(Base):
    """Customer accounts and contact information."""
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
    pppoe_credentials = relationship("PPPoECredential", back_populates="customer", uselist=False)
    password_history = relationship("PasswordHistory", back_populates="customer")


class Plan(Base):
    """Internet package/plan (managed by admin)."""
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)              # Display name: "10Mbps"
    group_name = Column(Text, unique=True, nullable=False)        # RADIUS group: "plan_a3f7k9"
    description = Column(Text)
    price = Column(Float, nullable=False) 
    bandwidth_up = Column(Integer, default=8192)                  # Kbps
    bandwidth_down = Column(Integer, default=8192)                # Kbps
    session_timeout = Column(Integer, default=86400)              # seconds
    idle_timeout = Column(Integer, default=600)                   # seconds
    simultaneous_use = Column(Integer, default=1)                 # max concurrent devices
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PPPoECredential(Base):
    """Permanent PPPoE credentials - NEVER changed once assigned.
    
    Separated from subscription so PPPoE username/password remains
    constant even if customer changes plans, cancels, or renews.
    """
    __tablename__ = "pppoe_credentials"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False)
    username = Column(Text, unique=True, nullable=False, index=True)
    password = Column(Text, nullable=False)                        # Cleartext for RADIUS
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    customer = relationship("Customer", back_populates="pppoe_credentials")
    
    __table_args__ = (
        CheckConstraint(
            "username ~ '^[a-z0-9_]+$'",
            name="ck_pppoe_username_format",
        ),
    )


class PasswordHistory(Base):
    """Audit trail for web portal password changes.
    
    Tracks every password change for security auditing.
    PPPoE passwords are NOT tracked here - they never change.
    """
    __tablename__ = "password_history"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    password_hash = Column(Text, nullable=False)                   # bcrypt hash
    changed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    changed_by = Column(Text)                                      # 'customer' or 'admin'
    ip_address = Column(Text)                                      # IP that made the change
    reason = Column(Text)                                          # 'user_request', 'admin_reset', 'security'
    
    customer = relationship("Customer", back_populates="password_history")


class Subscription(Base):
    """Customer subscriptions to plans.
    
    Links customer (and their permanent PPPoE credentials) to a plan.
    Subscription can change plans without changing PPPoE credentials.
    """
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(Text, default="trial")
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    cancelled_at = Column(DateTime(timezone=True))                 # When cancelled
    cancel_reason = Column(Text)                                   # Why cancelled
    
    customer = relationship("Customer", back_populates="subscriptions")
    plan = relationship("Plan")
    payments = relationship("Payment", back_populates="subscription")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('trial','active','expired','cancelled','suspended')",
            name="ck_sub_status",
        ),
    )


class Payment(Base):
    """Payment transaction records."""
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(Text, default="KSH")
    payment_method = Column(Text, default="simulated")
    external_ref = Column(Text)
    paid_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    received_by = Column(Text)                                     # Admin who received payment
    notes = Column(Text)
    
    subscription = relationship("Subscription", back_populates="payments")


class AuditLog(Base):
    """General audit trail for billing system changes.
    
    Tracks all important changes: plan changes, status changes,
    manual overrides, admin actions, etc.
    """
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    table_name = Column(Text, nullable=False)                      # Which table changed
    record_id = Column(Integer)                                    # Which record changed
    action = Column(Text, nullable=False)                          # 'INSERT', 'UPDATE', 'DELETE'
    field_name = Column(Text)                                      # Which field changed (NULL for INSERT/DELETE)
    old_value = Column(Text)                                       # Previous value
    new_value = Column(Text)                                       # New value
    changed_by = Column(Text)                                      # 'customer_id:5' or 'admin_id:1'
    ip_address = Column(Text)
    changed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    reason = Column(Text)                                          # Why the change was made


class Setting(Base):
    """Key-value settings table for company name, currency, etc."""
    __tablename__ = "settings"
    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
