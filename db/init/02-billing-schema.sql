-- Custom billing tables for WiFi subscription management
-- Runs after 01-freeradius-schema.sql on first container startup

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id          serial PRIMARY KEY,
    name        text NOT NULL,
    email       text UNIQUE NOT NULL,
    phone       text,
    address     text,
    created_at  timestamp with time zone NOT NULL DEFAULT now(),
    updated_at  timestamp with time zone NOT NULL DEFAULT now()
);

-- ============================================================
-- SUBSCRIPTION PLANS (templates, e.g. "30Mbps", "50Mbps")
-- ============================================================
CREATE TABLE IF NOT EXISTS plans (
    id              serial PRIMARY KEY,
    name            text NOT NULL UNIQUE,
    description     text,
    price_cents     integer NOT NULL,              -- price in cents (USD)
    bandwidth_up    integer,                       -- Kbps
    bandwidth_down  integer,                       -- Kbps
    session_timeout integer DEFAULT 86400,         -- seconds (default 24h)
    idle_timeout    integer DEFAULT 600,           -- seconds
    created_at      timestamp with time zone NOT NULL DEFAULT now()
);

-- ============================================================
-- SUBSCRIPTIONS (active/expired/cancelled per customer)
-- ============================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id                  serial PRIMARY KEY,
    customer_id         integer NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    plan_id             integer NOT NULL REFERENCES plans(id),
    username            text NOT NULL,             -- matches radcheck.UserName
    password            text NOT NULL,             -- Cleartext-Password for radcheck
    status              text NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'expired', 'cancelled', 'suspended')),
    current_period_start timestamp with time zone NOT NULL,
    current_period_end   timestamp with time zone NOT NULL,
    created_at          timestamp with time zone NOT NULL DEFAULT now(),
    updated_at          timestamp with time zone NOT NULL DEFAULT now(),
    UNIQUE (username)
);

-- ============================================================
-- PAYMENTS (ledger)
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
    id              serial PRIMARY KEY,
    subscription_id integer NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    amount_cents    integer NOT NULL,
    currency        text NOT NULL DEFAULT 'USD',
    payment_method  text NOT NULL DEFAULT 'cash',
    external_ref    text,                           -- payment gateway reference
    paid_at         timestamp with time zone NOT NULL DEFAULT now(),
    notes           text
);

-- ============================================================
-- HELPER FUNCTION: Same-date-next-month calculation
-- Handles Jan 31 → Feb 28 edge case
-- ============================================================
CREATE OR REPLACE FUNCTION same_date_next_month(d timestamp with time zone)
RETURNS timestamp with time zone AS $$
DECLARE
    next_month timestamp with time zone;
BEGIN
    next_month := d + INTERVAL '1 month';
    -- If the resulting day-of-month is different (e.g. Jan 31 → Feb 28),
    -- clamp to the last day of the next month
    IF EXTRACT(DAY FROM next_month) <> EXTRACT(DAY FROM d) THEN
        next_month := date_trunc('month', next_month) + INTERVAL '1 month' - INTERVAL '1 day'
                      + EXTRACT(HOUR FROM d) * INTERVAL '1 hour'
                      + EXTRACT(MINUTE FROM d) * INTERVAL '1 minute'
                      + EXTRACT(SECOND FROM d) * INTERVAL '1 second';
    END IF;
    RETURN next_month;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: extend_subscription
-- Called when a payment is received. Extends subscription by 1
-- month from current_period_end (or from NOW if already expired),
-- and updates radcheck.Expiration to match.
-- ============================================================
CREATE OR REPLACE FUNCTION extend_subscription(
    p_subscription_id integer,
    p_amount_cents integer,
    p_payment_method text DEFAULT 'cash',
    p_external_ref text DEFAULT NULL
)
RETURNS jsonb AS $$
DECLARE
    v_sub subscriptions%ROWTYPE;
    v_new_end timestamp with time zone;
    v_radcheck_id integer;
BEGIN
    -- Lock the subscription row
    SELECT * INTO v_sub FROM subscriptions WHERE id = p_subscription_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'subscription not found');
    END IF;

    -- Calculate new expiry: extend from current_period_end, or from now if already past
    IF v_sub.current_period_end > now() THEN
        v_new_end := same_date_next_month(v_sub.current_period_end);
    ELSE
        v_new_end := same_date_next_month(now());
    END IF;

    -- Update subscription
    UPDATE subscriptions
    SET current_period_end = v_new_end,
        status = 'active',
        updated_at = now()
    WHERE id = p_subscription_id;

    -- Record payment
    INSERT INTO payments (subscription_id, amount_cents, payment_method, external_ref)
    VALUES (p_subscription_id, p_amount_cents, p_payment_method, p_external_ref);

    -- Update radcheck.Expiration (upsert)
    INSERT INTO radcheck (UserName, Attribute, op, Value)
    VALUES (v_sub.username, 'Expiration', ':=',
            to_char(v_new_end, 'DD Mon YYYY HH24:MI:SS'))
    ON CONFLICT (id) DO NOTHING;  -- fall through to UPDATE below

    -- Update if already exists
    UPDATE radcheck
    SET Value = to_char(v_new_end, 'DD Mon YYYY HH24:MI:SS'),
        op = ':='
    WHERE UserName = v_sub.username AND Attribute = 'Expiration';

    RETURN jsonb_build_object(
        'username', v_sub.username,
        'new_expiry', v_new_end,
        'payment_id', currval(pg_get_serial_sequence('payments', 'id'))
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: create_customer_subscription
-- Creates a customer + subscription + radcheck entries in one call
-- ============================================================
CREATE OR REPLACE FUNCTION create_customer_subscription(
    p_name          text,
    p_email         text,
    p_phone         text DEFAULT NULL,
    p_plan_name     text DEFAULT '30Mbps',
    p_username      text DEFAULT NULL,
    p_password      text DEFAULT NULL,
    p_pay_now       boolean DEFAULT TRUE,
    p_amount_cents  integer DEFAULT NULL
)
RETURNS jsonb AS $$
DECLARE
    v_customer_id integer;
    v_plan_id integer;
    v_plan plans%ROWTYPE;
    v_username text := COALESCE(p_username, 'user_' || floor(random() * 1000000)::text);
    v_password text := COALESCE(p_password, md5(random()::text));
    v_sub_id integer;
    v_start timestamp with time zone := now();
    v_end timestamp with time zone;
BEGIN
    -- Find or create plan
    SELECT * INTO v_plan FROM plans WHERE name = p_plan_name;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'plan not found: ' || p_plan_name);
    END IF;

    -- Create customer
    INSERT INTO customers (name, email, phone)
    VALUES (p_name, p_email, p_phone)
    RETURNING id INTO v_customer_id;

    -- Create subscription (30 days initially)
    v_end := same_date_next_month(v_start);

    INSERT INTO subscriptions (customer_id, plan_id, username, password, current_period_start, current_period_end)
    VALUES (v_customer_id, v_plan.id, v_username, v_password, v_start, v_end)
    RETURNING id INTO v_sub_id;

    -- Seed radcheck with password and expiration
    INSERT INTO radcheck (UserName, Attribute, op, Value) VALUES
        (v_username, 'Cleartext-Password', ':=', v_password),
        (v_username, 'Expiration', ':=', to_char(v_end, 'DD Mon YYYY HH24:MI:SS'));

    -- Seed radusergroup
    INSERT INTO radusergroup (UserName, GroupName, priority)
    VALUES (v_username, p_plan_name, 1);

    -- Seed radreply with Session-Timeout from plan
    INSERT INTO radreply (UserName, Attribute, op, Value)
    VALUES (v_username, 'Session-Timeout', ':=', v_plan.session_timeout::text);

    -- If pay_now, record payment and extend
    IF p_pay_now THEN
        PERFORM extend_subscription(
            v_sub_id,
            COALESCE(p_amount_cents, v_plan.price_cents),
            'cash',
            'initial'
        );
    END IF;

    RETURN jsonb_build_object(
        'customer_id', v_customer_id,
        'subscription_id', v_sub_id,
        'username', v_username,
        'password', v_password,
        'expires', v_end
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA
-- ============================================================

-- Plans
INSERT INTO plans (name, description, price_cents, bandwidth_up, bandwidth_down, session_timeout, idle_timeout) VALUES
    ('10Mbps',   'Basic - 10 Mbps',   1000,   10240,  10240,  86400, 600),
    ('30Mbps',   'Standard - 30 Mbps', 2000,  30720,  30720,  86400, 600),
    ('50Mbps',   'Premium - 50 Mbps',  3000,  51200,  51200,  86400, 600)
ON CONFLICT (name) DO NOTHING;

-- Test customer: active subscription
SELECT create_customer_subscription(
    'Test User Active',
    'test@example.com',
    '+1234567890',
    '30Mbps',
    'test_active',
    'testpass123',
    TRUE,
    2000
);

-- Test customer: expired subscription (Expiration set to yesterday)
-- We create it then manually backdate
DO $$
DECLARE
    v_yesterday timestamp with time zone := now() - INTERVAL '2 days';
    v_result jsonb;
BEGIN
    v_result := create_customer_subscription(
        'Test User Expired',
        'expired@example.com',
        NULL,
        '10Mbps',
        'test_expired',
        'expired123',
        FALSE,       -- don't pay
        NULL
    );

    -- Backdate the expiry to 2 days ago
    UPDATE subscriptions
    SET current_period_end = now() - INTERVAL '1 day',
        status = 'expired',
        updated_at = now()
    WHERE username = 'test_expired';

    UPDATE radcheck
    SET Value = to_char(v_yesterday, 'DD Mon YYYY HH24:MI:SS')
    WHERE username = 'test_expired' AND Attribute = 'Expiration';
END;
$$;
