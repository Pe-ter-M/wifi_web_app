-- ============================================================
-- WiFi Subscription Management System
-- Complete Database Schema
-- ============================================================

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id              serial PRIMARY KEY,
    name            text NOT NULL,
    email           text UNIQUE,
    phone           text,
    address         text,
    is_admin        boolean NOT NULL DEFAULT false,
    password_hash   text,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    updated_at      timestamp with time zone NOT NULL DEFAULT now()
);

-- ============================================================
-- SUBSCRIPTION PLANS (monthly packages)
-- ============================================================
CREATE TABLE IF NOT EXISTS plans (
    id                  serial PRIMARY KEY,
    name                text NOT NULL UNIQUE,
    group_name          text NOT NULL UNIQUE,
    description         text,
    price               float NOT NULL,
    bandwidth_up        integer NOT NULL DEFAULT 8192,
    bandwidth_down      integer NOT NULL DEFAULT 8192,
    session_timeout     integer NOT NULL DEFAULT 86400,
    idle_timeout        integer NOT NULL DEFAULT 600,
    simultaneous_use    integer NOT NULL DEFAULT 1,
    is_active           boolean NOT NULL DEFAULT true,
    sort_order          integer NOT NULL DEFAULT 0,
    created_at          timestamp with time zone NOT NULL DEFAULT now(),
    updated_at          timestamp with time zone NOT NULL DEFAULT now()
);

-- ============================================================
-- PPPoE CREDENTIALS (permanent, never changed once assigned)
-- ============================================================
CREATE TABLE IF NOT EXISTS pppoe_credentials (
    id              serial PRIMARY KEY,
    customer_id     integer NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
    username        text NOT NULL UNIQUE,
    password        text NOT NULL,
    is_active       boolean NOT NULL DEFAULT true,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    updated_at      timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT ck_pppoe_username_format CHECK (username ~ '^[a-z0-9_]+$')
);

CREATE INDEX IF NOT EXISTS idx_pppoe_username ON pppoe_credentials (username);
CREATE INDEX IF NOT EXISTS idx_pppoe_customer_id ON pppoe_credentials (customer_id);

-- ============================================================
-- PASSWORD HISTORY (web portal password audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS password_history (
    id              serial PRIMARY KEY,
    customer_id     integer NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    password_hash   text NOT NULL,
    changed_at      timestamp with time zone NOT NULL DEFAULT now(),
    changed_by      text,
    ip_address      text,
    reason          text
);

CREATE INDEX IF NOT EXISTS idx_password_history_customer ON password_history (customer_id);

-- ============================================================
-- SUBSCRIPTIONS (links customer to plan)
-- ============================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      serial PRIMARY KEY,
    customer_id             integer NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    plan_id                 integer NOT NULL REFERENCES plans(id),
    status                  text NOT NULL DEFAULT 'trial',
    current_period_start    timestamp with time zone NOT NULL,
    current_period_end      timestamp with time zone NOT NULL,
    cancelled_at            timestamp with time zone,
    cancel_reason           text,
    created_at              timestamp with time zone NOT NULL DEFAULT now(),
    updated_at              timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT ck_sub_status CHECK (status IN ('trial','active','expired','cancelled','suspended'))
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_customer_id ON subscriptions (customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions (status);

-- ============================================================
-- PAYMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
    id                  serial PRIMARY KEY,
    subscription_id     integer NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    amount              float NOT NULL,
    currency            text NOT NULL DEFAULT 'KSH',
    payment_method      text NOT NULL DEFAULT 'simulated',
    external_ref        text,
    received_by         text,
    paid_at             timestamp with time zone NOT NULL DEFAULT now(),
    notes               text
);

CREATE INDEX IF NOT EXISTS idx_payments_subscription ON payments (subscription_id);

-- ============================================================
-- AUDIT LOGS (general billing audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              serial PRIMARY KEY,
    table_name      text NOT NULL,
    record_id       integer,
    action          text NOT NULL,
    field_name      text,
    old_value       text,
    new_value       text,
    changed_by      text,
    ip_address      text,
    changed_at      timestamp with time zone NOT NULL DEFAULT now(),
    reason          text
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_table ON audit_logs (table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_date ON audit_logs (changed_at);

-- ============================================================
-- SYSTEM SETTINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key             text PRIMARY KEY,
    value           text NOT NULL,
    updated_at      timestamp with time zone NOT NULL DEFAULT now()
);
-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- ============================================================
-- 1. same_date_next_month
-- Utility: Adds one month to a date, handling month-end edge cases
-- Used by: create_subscription_from_payment
-- ============================================================
CREATE OR REPLACE FUNCTION same_date_next_month(d timestamp with time zone)
RETURNS timestamp with time zone AS $$
DECLARE
    next_month timestamp with time zone;
BEGIN
    next_month := d + INTERVAL '1 month';
    
    -- Clamp to last day of month if original day exceeds next month's days
    -- Example: Jan 31 → Feb 28, not Feb 31 (invalid)
    IF EXTRACT(DAY FROM next_month) <> EXTRACT(DAY FROM d) THEN
        next_month := date_trunc('month', next_month) + INTERVAL '1 month' - INTERVAL '1 day'
                      + EXTRACT(HOUR FROM d) * INTERVAL '1 hour'
                      + EXTRACT(MINUTE FROM d) * INTERVAL '1 minute'
                      + EXTRACT(SECOND FROM d) * INTERVAL '1 second';
    END IF;
    
    RETURN next_month;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- 2. generate_pppoe_credentials
-- Creates permanent PPPoE credentials for a customer
-- Username format: user_XXXXXXXX (8 random chars)
-- Password: 12 random characters
-- These credentials NEVER change for the lifetime of the customer
-- ============================================================
CREATE OR REPLACE FUNCTION generate_pppoe_credentials(p_customer_id integer)
RETURNS jsonb AS $$
DECLARE
    v_username text;
    v_password text;
    v_cred_id integer;
BEGIN
    -- Check customer exists
    IF NOT EXISTS (SELECT 1 FROM customers WHERE id = p_customer_id) THEN
        RETURN jsonb_build_object('error', 'Customer not found');
    END IF;
    
    -- Check if credentials already exist
    IF EXISTS (SELECT 1 FROM pppoe_credentials WHERE customer_id = p_customer_id) THEN
        RETURN jsonb_build_object('error', 'Customer already has PPPoE credentials');
    END IF;
    
    -- Generate unique username
    LOOP
        v_username := 'user_' || substring(md5(random()::text || clock_timestamp()::text) from 1 for 8);
        EXIT WHEN NOT EXISTS (SELECT 1 FROM pppoe_credentials WHERE username = v_username);
    END LOOP;
    
    -- Generate random password
    v_password := substring(md5(random()::text || clock_timestamp()::text) from 1 for 12);
    
    -- Insert permanent credentials
    INSERT INTO pppoe_credentials (customer_id, username, password)
    VALUES (p_customer_id, v_username, v_password)
    RETURNING id INTO v_cred_id;
    
    RETURN jsonb_build_object(
        'credential_id', v_cred_id,
        'username', v_username,
        'password', v_password
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 3. sync_plan_to_radius (TRIGGER VERSION)
-- Copies plan settings to RADIUS group tables
-- Called automatically by TRIGGER on plans INSERT/UPDATE
-- ============================================================
CREATE OR REPLACE FUNCTION sync_plan_to_radius()
RETURNS trigger AS $$
DECLARE
    v_group_name text;
BEGIN
    v_group_name := NEW.group_name;
    
    -- Remove old group settings for clean sync
    DELETE FROM radgroupcheck WHERE GroupName = v_group_name;
    DELETE FROM radgroupreply WHERE GroupName = v_group_name;
    
    -- Insert group check (restrictions enforced before access)
    INSERT INTO radgroupcheck (GroupName, Attribute, op, Value)
    VALUES (v_group_name, 'Simultaneous-Use', ':=', NEW.simultaneous_use::text);
    
    -- Insert group replies (policies applied after authentication)
    INSERT INTO radgroupreply (GroupName, Attribute, op, Value) VALUES
        (v_group_name, 'Mikrotik-Rate-Limit', ':=', 
         NEW.bandwidth_down::text || 'k/' || NEW.bandwidth_up::text || 'k'),
        (v_group_name, 'Session-Timeout', ':=', NEW.session_timeout::text),
        (v_group_name, 'Idle-Timeout', ':=', NEW.idle_timeout::text),
        (v_group_name, 'Acct-Interim-Interval', ':=', '300');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 4. cleanup_plan_radius
-- Removes all RADIUS group data for a plan
-- Called BEFORE deleting a plan (after verifying no subscriptions exist)
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_plan_radius(p_plan_id integer)
RETURNS void AS $$
DECLARE
    v_group_name text;
BEGIN
    SELECT group_name INTO v_group_name FROM plans WHERE id = p_plan_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Plan ID % not found', p_plan_id;
    END IF;
    
    -- Remove all RADIUS references to this plan's group
    DELETE FROM radgroupcheck WHERE GroupName = v_group_name;
    DELETE FROM radgroupreply WHERE GroupName = v_group_name;
    DELETE FROM radusergroup WHERE GroupName = v_group_name;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 5a. sync_subscription_to_radius (MANUAL VERSION - with parameter)
-- Used by create_subscription_from_payment and manual calls
-- ============================================================
CREATE OR REPLACE FUNCTION sync_subscription_to_radius(p_subscription_id integer)
RETURNS void AS $$
DECLARE
    v_sub subscriptions%ROWTYPE;
    v_plan plans%ROWTYPE;
    v_pppoe pppoe_credentials%ROWTYPE;
BEGIN
    SELECT * INTO v_sub FROM subscriptions WHERE id = p_subscription_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Subscription ID % not found', p_subscription_id;
    END IF;
    
    SELECT * INTO v_plan FROM plans WHERE id = v_sub.plan_id;
    
    SELECT * INTO v_pppoe FROM pppoe_credentials 
    WHERE customer_id = v_sub.customer_id AND is_active = TRUE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active PPPoE credentials for customer ID %', v_sub.customer_id;
    END IF;
    
    DELETE FROM radcheck WHERE UserName = v_pppoe.username;
    DELETE FROM radusergroup WHERE UserName = v_pppoe.username;
    
    INSERT INTO radcheck (UserName, Attribute, op, Value) VALUES
        (v_pppoe.username, 'Cleartext-Password', ':=', v_pppoe.password),
        (v_pppoe.username, 'Expiration', ':=', 
         to_char(v_sub.current_period_end, 'DD Mon YYYY HH24:MI:SS'));
    
    INSERT INTO radusergroup (UserName, GroupName, priority)
    VALUES (v_pppoe.username, v_plan.group_name, 0);
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 5b. trg_sync_subscription_to_radius (TRIGGER VERSION - no params)
-- Called automatically by TRIGGER on subscriptions INSERT/UPDATE
-- ============================================================
CREATE OR REPLACE FUNCTION trg_sync_subscription_to_radius()
RETURNS trigger AS $$
BEGIN
    PERFORM sync_subscription_to_radius(NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 6. cleanup_subscription_radius (TRIGGER VERSION)
-- Removes user's RADIUS entries when subscription is deleted
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_subscription_radius()
RETURNS trigger AS $$
DECLARE
    v_pppoe pppoe_credentials%ROWTYPE;
BEGIN
    -- Get PPPoE username to remove from RADIUS
    SELECT * INTO v_pppoe FROM pppoe_credentials WHERE customer_id = OLD.customer_id;
    
    IF FOUND THEN
        -- Remove user-specific RADIUS entries only
        DELETE FROM radcheck WHERE UserName = v_pppoe.username;
        DELETE FROM radusergroup WHERE UserName = v_pppoe.username;
        DELETE FROM radreply WHERE UserName = v_pppoe.username;
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 7. create_subscription_from_payment
-- Handles the full payment → subscription → RADIUS flow
-- For new subscriptions: creates subscription and processes payment
-- For existing active subscriptions: extends expiry by one month
-- For expired subscriptions: reactivates from today + one month
-- ============================================================
CREATE OR REPLACE FUNCTION create_subscription_from_payment(
    p_customer_id       integer,
    p_plan_name         text,
    p_amount            float,
    p_payment_method    text DEFAULT 'simulated',
    p_external_ref      text DEFAULT NULL,
    p_received_by       text DEFAULT NULL
)
RETURNS jsonb AS $$
DECLARE
    v_plan plans%ROWTYPE;
    v_sub_id integer;
    v_existing_sub subscriptions%ROWTYPE;
    v_new_end timestamp with time zone;
    v_start timestamp with time zone := now();
    v_pppoe pppoe_credentials%ROWTYPE;
BEGIN
    -- Find the plan
    SELECT * INTO v_plan FROM plans WHERE name = p_plan_name;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Plan not found: ' || p_plan_name);
    END IF;
    
    -- Verify customer has PPPoE credentials
    SELECT * INTO v_pppoe FROM pppoe_credentials 
    WHERE customer_id = p_customer_id AND is_active = TRUE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Customer has no active PPPoE credentials. Generate credentials first.');
    END IF;
    
    -- Check for existing active subscription
    SELECT * INTO v_existing_sub FROM subscriptions 
    WHERE customer_id = p_customer_id AND status = 'active'
    ORDER BY current_period_end DESC LIMIT 1;
    
    IF FOUND THEN
        -- Extend existing subscription from its current end date
        v_new_end := same_date_next_month(v_existing_sub.current_period_end);
        
        UPDATE subscriptions
        SET current_period_end = v_new_end,
            updated_at = now()
        WHERE id = v_existing_sub.id;
        
        v_sub_id := v_existing_sub.id;
        
    ELSE
        -- Check for expired subscription to reactivate
        SELECT * INTO v_existing_sub FROM subscriptions 
        WHERE customer_id = p_customer_id AND status = 'expired'
        ORDER BY current_period_end DESC LIMIT 1;
        
        IF FOUND THEN
            -- Reactivate from today
            v_new_end := same_date_next_month(v_start);
            
            UPDATE subscriptions
            SET plan_id = v_plan.id,
                status = 'active',
                current_period_start = v_start,
                current_period_end = v_new_end,
                updated_at = now()
            WHERE id = v_existing_sub.id;
            
            v_sub_id := v_existing_sub.id;
            
        ELSE
            -- Create new subscription
            v_new_end := same_date_next_month(v_start);
            
            INSERT INTO subscriptions (customer_id, plan_id, status, current_period_start, current_period_end)
            VALUES (p_customer_id, v_plan.id, 'active', v_start, v_new_end)
            RETURNING id INTO v_sub_id;
        END IF;
    END IF;
    
    -- Record payment
    INSERT INTO payments (subscription_id, amount, payment_method, external_ref, received_by)
    VALUES (v_sub_id, p_amount, p_payment_method, p_external_ref, p_received_by);
    
    -- Sync to RADIUS (trigger handles this, but call explicitly for immediate effect)
    PERFORM sync_subscription_to_radius(v_sub_id);
    
    RETURN jsonb_build_object(
        'subscription_id', v_sub_id,
        'username', v_pppoe.username,
        'new_expiry', v_new_end,
        'amount_paid', p_amount,
        'payment_id', currval(pg_get_serial_sequence('payments', 'id'))
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 8. deactivate_expired_subscriptions
-- Finds all subscriptions past their end date and deactivates them
-- Removes RADIUS entries so users cannot authenticate
-- Run manually via cron job or admin action (daily recommended)
-- ============================================================
CREATE OR REPLACE FUNCTION deactivate_expired_subscriptions()
RETURNS jsonb AS $$
DECLARE
    v_count integer := 0;
    v_sub record;
BEGIN
    -- Find all subscriptions that expired but still show as active or trial
    FOR v_sub IN 
        SELECT id, customer_id, username 
        FROM subscriptions s
        JOIN pppoe_credentials p ON p.customer_id = s.customer_id
        WHERE s.status IN ('active', 'trial') 
          AND s.current_period_end < now()
    LOOP
        -- Remove RADIUS access
        DELETE FROM radcheck WHERE UserName = v_sub.username;
        DELETE FROM radusergroup WHERE UserName = v_sub.username;
        
        -- Mark subscription as expired
        UPDATE subscriptions 
        SET status = 'expired', updated_at = now()
        WHERE id = v_sub.id;
        
        v_count := v_count + 1;
    END LOOP;
    
    RETURN jsonb_build_object(
        'expired_count', v_count,
        'processed_at', now()
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 9. get_customer_usage
-- Returns usage statistics for a customer from radacct
-- Includes: total time, total data, active sessions, last connection
-- ============================================================
CREATE OR REPLACE FUNCTION get_customer_usage(p_customer_id integer)
RETURNS jsonb AS $$
DECLARE
    v_username text;
    v_result jsonb;
BEGIN
    -- Get PPPoE username
    SELECT username INTO v_username FROM pppoe_credentials 
    WHERE customer_id = p_customer_id AND is_active = TRUE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'No active PPPoE credentials found');
    END IF;
    
    -- Aggregate usage from radacct
    SELECT jsonb_build_object(
        'username', v_username,
        'active_sessions', (
            SELECT COUNT(*) FROM radacct 
            WHERE UserName = v_username AND AcctStopTime IS NULL
        ),
        'total_time_seconds', (
            SELECT COALESCE(SUM(AcctSessionTime), 0) FROM radacct 
            WHERE UserName = v_username
        ),
        'total_download_bytes', (
            SELECT COALESCE(SUM(AcctInputOctets), 0) FROM radacct 
            WHERE UserName = v_username
        ),
        'total_upload_bytes', (
            SELECT COALESCE(SUM(AcctOutputOctets), 0) FROM radacct 
            WHERE UserName = v_username
        ),
        'last_connected', (
            SELECT MAX(AcctStartTime) FROM radacct 
            WHERE UserName = v_username
        ),
        'current_session_start', (
            SELECT MAX(AcctStartTime) FROM radacct 
            WHERE UserName = v_username AND AcctStopTime IS NULL
        )
    ) INTO v_result;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 10. delete_customer
-- Completely removes a customer and ALL related data
-- Application MUST verify no active subscriptions before calling
-- Cleans: radcheck, radusergroup, radreply, pppoe_credentials,
--         password_history, subscriptions (cascades to payments), customers
-- ============================================================
CREATE OR REPLACE FUNCTION delete_customer(p_customer_id integer)
RETURNS jsonb AS $$
DECLARE
    v_customer_name text;
    v_pppoe_username text;
    v_sub_count integer;
    v_payment_count integer;
BEGIN
    -- Get customer info for logging
    SELECT name INTO v_customer_name FROM customers WHERE id = p_customer_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('error', 'Customer not found');
    END IF;
    
    -- Safety check: verify no active subscriptions
    IF EXISTS (
        SELECT 1 FROM subscriptions 
        WHERE customer_id = p_customer_id AND status IN ('active', 'trial')
    ) THEN
        RETURN jsonb_build_object(
            'error', 'Cannot delete customer with active subscriptions. Deactivate them first.',
            'customer_id', p_customer_id
        );
    END IF;
    
    -- Count what will be deleted
    SELECT COUNT(*) INTO v_sub_count FROM subscriptions WHERE customer_id = p_customer_id;
    SELECT COUNT(*) INTO v_payment_count FROM payments 
    WHERE subscription_id IN (SELECT id FROM subscriptions WHERE customer_id = p_customer_id);
    
    -- Get PPPoE username for RADIUS cleanup
    SELECT username INTO v_pppoe_username FROM pppoe_credentials WHERE customer_id = p_customer_id;
    
    -- Remove RADIUS entries
    IF v_pppoe_username IS NOT NULL THEN
        DELETE FROM radcheck WHERE UserName = v_pppoe_username;
        DELETE FROM radusergroup WHERE UserName = v_pppoe_username;
        DELETE FROM radreply WHERE UserName = v_pppoe_username;
    END IF;
    
    -- Remove PPPoE credentials
    DELETE FROM pppoe_credentials WHERE customer_id = p_customer_id;
    
    -- Remove password history
    DELETE FROM password_history WHERE customer_id = p_customer_id;
    
    -- Remove subscriptions (cascades to payments via FK)
    DELETE FROM subscriptions WHERE customer_id = p_customer_id;
    
    -- Finally, remove the customer
    DELETE FROM customers WHERE id = p_customer_id;
    
    RETURN jsonb_build_object(
        'deleted', true,
        'customer_name', v_customer_name,
        'pppoe_username', v_pppoe_username,
        'subscriptions_removed', v_sub_count,
        'payments_removed', v_payment_count,
        'deleted_at', now()
    );
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-sync plan settings to RADIUS on create/update
DROP TRIGGER IF EXISTS trg_plan_sync ON plans;
CREATE TRIGGER trg_plan_sync
AFTER INSERT OR UPDATE ON plans
FOR EACH ROW EXECUTE FUNCTION sync_plan_to_radius();

-- Auto-sync subscription to RADIUS on create/update
DROP TRIGGER IF EXISTS trg_sub_sync ON subscriptions;
CREATE TRIGGER trg_sub_sync
AFTER INSERT OR UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION trg_sync_subscription_to_radius();

-- Auto-cleanup RADIUS when subscription is deleted
DROP TRIGGER IF EXISTS trg_sub_cleanup ON subscriptions;
CREATE TRIGGER trg_sub_cleanup
BEFORE DELETE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION cleanup_subscription_radius();

-- ============================================================
-- SEED DATA
-- ============================================================

-- ============================================================
-- SYSTEM SETTINGS
-- ============================================================
INSERT INTO settings (key, value) VALUES
    ('company', '{"name":"Phantom Internet Providers","short_name":"PhantomNet","tagline":"Connect with confidence","currency":"KSH","currency_symbol":"KSh","support_email":"support@phantomnet.co.ke","support_phone":"+254 700 000000"}'),
    ('defaults', '{"max_devices":1,"session_timeout":86400,"idle_timeout":600,"trial_days":3,"subscription_days":30}'),
    ('billing', '{"currency":"KSH","payment_methods":["cash","mpesa","bank_transfer","simulated"],"invoice_prefix":"INV-"}')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- PLANS (auto-syncs to RADIUS groups via trigger on insert)
-- ============================================================
INSERT INTO plans (name, group_name, description, price, bandwidth_up, bandwidth_down, session_timeout, idle_timeout, simultaneous_use, is_active, sort_order) VALUES
    ('10Mbps',   'plan_10mbps',   'Basic - 10 Mbps',          1000.00, 10240,  10240,  86400, 600, 1, true, 1),
    ('20Mbps',   'plan_20mbps',   'Standard - 20 Mbps',       2000.00, 20480,  20480,  86400, 600, 1, true, 2),
    ('30Mbps',   'plan_30mbps',   'Premium - 30 Mbps',        3000.00, 30720,  30720,  86400, 600, 2, true, 3),
    ('50Mbps',   'plan_50mbps',   'Ultimate - 50 Mbps',       5000.00, 51200,  51200,  86400, 600, 2, true, 4),
    ('100Mbps',  'plan_100mbps',  'Business - 100 Mbps',     10000.00, 102400, 102400, 86400, 600, 3, true, 5)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- ADMIN USER
-- ============================================================
-- WEB PORTAL LOGIN: admin@phantomnet.co.ke / admin123
-- ============================================================
INSERT INTO customers (name, email, phone, address, is_admin, password_hash) VALUES
    ('Admin User', 'admin@phantomnet.co.ke', '+254700000000', 'Main Office', true, 
     '$2b$12$c5CYCSNWz0rN7O9dV/QzsOTCEpyd.J8eZhSA8IOBC1lJh//m.w9m6')  
ON CONFLICT (email) DO NOTHING;

-- ============================================================
-- TEST USER 1: Active subscription on 30Mbps
-- ============================================================
-- WEB PORTAL LOGIN: test_active@example.com / customer123
-- PPPoE LOGIN: test_active / active123
-- ============================================================
DO $$
DECLARE
    v_customer_id integer;
BEGIN
    -- Create customer
    INSERT INTO customers (name, email, phone, address, password_hash) VALUES
        ('Test Active User', 'test_active@example.com', '+254700000001', 'Nairobi, Kenya',
         '$2b$12$EvD5pPmcdsGo5YfgxcMeo.dUcCs/7X68OJ0bu0ttEWYnnHutJKEsm')  
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO v_customer_id;
    
    -- Generate permanent PPPoE credentials
    IF NOT EXISTS (SELECT 1 FROM pppoe_credentials WHERE customer_id = v_customer_id) THEN
        INSERT INTO pppoe_credentials (customer_id, username, password)
        VALUES (v_customer_id, 'test_active', 'active123');  -- ← CLEARTEXT password for PPPoE
    END IF;
    
    -- Create active subscription via payment
    PERFORM create_subscription_from_payment(
        p_customer_id := v_customer_id,
        p_plan_name := '30Mbps',
        p_amount := 3000.00,
        p_payment_method := 'simulated',
        p_external_ref := 'seed_active',
        p_received_by := 'seed_script'
    );
END;
$$;

-- ============================================================
-- TEST USER 2: Expired subscription on 10Mbps
-- ============================================================
-- WEB PORTAL LOGIN: test_expired@example.com / customer123
-- PPPoE LOGIN: test_expired / expired123
-- ============================================================
DO $$
DECLARE
    v_customer_id integer;
    v_plan plans%ROWTYPE;
    v_sub_id integer;
    v_start timestamp with time zone := now() - INTERVAL '32 days';
    v_end timestamp with time zone := now() - INTERVAL '2 days';
BEGIN
    -- Create customer
    INSERT INTO customers (name, email, phone, address, password_hash) VALUES
        ('Test Expired User', 'test_expired@example.com', '+254700000002', 'Kisumu, Kenya',
         '$2b$12$EvD5pPmcdsGo5YfgxcMeo.dUcCs/7X68OJ0bu0ttEWYnnHutJKEsm')  -- ← REPLACE WITH ACTUAL HASH
    ON CONFLICT (email) DO NOTHING
    RETURNING id INTO v_customer_id;
    
    -- Generate permanent PPPoE credentials
    IF NOT EXISTS (SELECT 1 FROM pppoe_credentials WHERE customer_id = v_customer_id) THEN
        INSERT INTO pppoe_credentials (customer_id, username, password)
        VALUES (v_customer_id, 'test_expired', 'expired123');  -- ← CLEARTEXT password for PPPoE
    END IF;
    
    -- Get plan
    SELECT * INTO v_plan FROM plans WHERE name = '10Mbps';
    
    -- Create expired subscription
    INSERT INTO subscriptions (customer_id, plan_id, status, current_period_start, current_period_end)
    VALUES (v_customer_id, v_plan.id, 'expired', v_start, v_end)
    RETURNING id INTO v_sub_id;
    
    -- Record historical payment
    INSERT INTO payments (subscription_id, amount, payment_method, external_ref, received_by, paid_at)
    VALUES (v_sub_id, 1000.00, 'simulated', 'seed_expired', 'seed_script', v_start);
    
    -- Set RADIUS expiry to past date so FreeRADIUS rejects authentication
    UPDATE radcheck
    SET Value = to_char(v_end, 'DD Mon YYYY HH24:MI:SS')
    WHERE UserName = 'test_expired' AND Attribute = 'Expiration';
END;
$$;

-- ============================================================
-- NAS DEVICE (for testing RADIUS connectivity locally)
-- ============================================================
-- Docker network clients (172.16.0.0/12)
INSERT INTO nas (nasname, shortname, type, ports, secret, description) VALUES
    ('172.16.0.0/12', 'docker-nas', 'other', 0, 'testing123', 'Docker bridge network - all containers')
ON CONFLICT DO NOTHING;

-- Localhost for testing
INSERT INTO nas (nasname, shortname, type, ports, secret, description) VALUES
    ('127.0.0.1', 'localhost', 'other', 0, 'testing123', 'Localhost testing')
ON CONFLICT DO NOTHING;

-- Localhost IPv6
INSERT INTO nas (nasname, shortname, type, ports, secret, description) VALUES
    ('::1', 'localhost-v6', 'other', 0, 'testing123', 'Localhost IPv6 testing')
ON CONFLICT DO NOTHING;