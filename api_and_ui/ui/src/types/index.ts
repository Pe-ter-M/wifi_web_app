export interface CompanyInfo {
  name: string;
  short_name: string;
  tagline: string;
  currency: string;
  currency_symbol: string;
  support_email: string;
  support_phone: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  is_admin: boolean;
  customer_id: number | null;
  customer_name: string | null;
}

export interface UserInfo {
  customer_id: number;
  name: string;
  email: string;
  phone: string | null;
  is_admin: boolean;
}

// ⚠️ CHANGED: price_cents/price_display → price, added group_name, simultaneous_use
export interface Plan {
  id: number;
  name: string;
  group_name: string;
  description: string | null;
  price: number;                    // Was price_cents + price_display
  bandwidth_up: number;
  bandwidth_down: number;
  session_timeout: number;
  idle_timeout: number;
  simultaneous_use: number;         // NEW
  is_active: boolean;
  sort_order: number;
  created_at?: string;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  address: string | null;
  is_admin: boolean;
  created_at: string;
  has_pppoe: boolean;         
  pppoe_username: string | null; 
}

// ⚠️ CHANGED: No username/password here anymore
export interface Subscription {
  id: number;
  customer_id: number;
  plan_id: number;
  status: string;
  current_period_start: string;
  current_period_end: string;
  cancelled_at: string | null;
  cancel_reason: string | null;
  created_at: string;
}

export interface SubscriptionStatus {
  id: number;
  username: string;
  status: string;
  plan_name: string;
  price: number;                    // Was price_display
  expires_at: string;
  is_active: boolean;
  days_remaining: number;
  device_count: number;
  max_devices: number;
  last_seen: string | null;
}

// ⚠️ CHANGED: price_display → price, simplified
export interface MyCredential {
  id: number;
  username: string;
  password: string;
  status: string;
  plan_name: string;
  price: number;                    // Was price_display
  expires_at: string | null;
  is_active: boolean;
  days_remaining: number;
  device_count: number;
  max_devices: number;
  last_seen: string | null;
  pppoe_active: boolean;            // NEW
}

// ⚠️ CHANGED: amount_cents/amount_display → amount
export interface Payment {
  id: number;
  subscription_id: number;
  amount: number;                   // Was amount_cents + amount_display
  currency: string;
  payment_method: string;
  external_ref: string | null;
  received_by: string | null;
  paid_at: string;
  notes: string | null;
  new_expiry: string | null;
  username: string | null;
}

export interface LiveSession {
  radacct_id: number;
  username: string;
  nas_ip: string;
  start_time: string | null;
  session_time: number;
  input_bytes: number;
  output_bytes: number;
  framed_ip: string | null;
}

export interface AuthLogEntry {
  id: number;
  username: string;
  reply: string;
  authdate: string;
}

// ⚠️ CHANGED: revenue_today_cents/revenue_this_month_cents → revenue_today/revenue_this_month
export interface DashboardStats {
  total_customers: number;
  active_subscriptions: number;
  expired_subscriptions: number;
  live_sessions: number;
  revenue_today: number;            // Was revenue_today_cents
  revenue_this_month: number;       // Was revenue_this_month_cents
}