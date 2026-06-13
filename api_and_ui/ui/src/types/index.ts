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

export interface Plan {
  id: number;
  name: string;
  description: string | null;
  price_cents: number;
  price_display: number;
  bandwidth_up: number;
  bandwidth_down: number;
  session_timeout: number;
  idle_timeout: number;
  is_active: boolean;
  sort_order: number;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  address: string | null;
  is_admin: boolean;
  created_at: string;
}

export interface Subscription {
  id: number;
  customer_id: number;
  plan_id: number;
  username: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  created_at: string;
}

export interface SubscriptionStatus {
  username: string;
  status: string;
  plan_name: string;
  expires_at: string;
  is_active: boolean;
  days_remaining: number;
  max_devices: number;
  current_device_count: number;
  last_seen: string | null;
}

export interface MyCredential {
  id: number;
  username: string;
  password: string;
  status: string;
  plan_name: string;
  price_display: number;
  expires_at: string | null;
  is_active: boolean;
  is_trial: boolean;
  days_remaining: number;
  hours_remaining: number;
  mins_remaining: number;
  secs_remaining: number;
  total_seconds_remaining: number;
  device_count: number;
  max_devices: number;
  last_seen: string | null;
}

export interface Payment {
  id: number;
  subscription_id: number;
  amount_cents: number;
  amount_display: number | null;
  currency: string;
  payment_method: string;
  paid_at: string;
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

export interface DashboardStats {
  total_customers: number;
  active_subscriptions: number;
  expired_subscriptions: number;
  live_sessions: number;
  revenue_today_cents: number;
  revenue_this_month_cents: number;
}
