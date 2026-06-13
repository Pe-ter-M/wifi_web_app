import axios from 'axios';
import type {
  LoginRequest, TokenResponse, UserInfo, CompanyInfo,
  Plan, Customer, Subscription, SubscriptionStatus, Payment,
  LiveSession, AuthLogEntry, DashboardStats, MyCredential,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auth ──────────────────────────────────────────────────
export const authApi = {
  login: (data: LoginRequest) =>
    api.post<TokenResponse>('/auth/login', data).then(r => r.data),
  me: () =>
    api.get<UserInfo>('/auth/me').then(r => r.data),
  logout: () =>
    api.post('/auth/logout').then(r => r.data),
};

// ── Settings ──────────────────────────────────────────────
export const settingsApi = {
  get: () =>
    api.get<{ company: CompanyInfo; defaults: Record<string, unknown> }>('/settings').then(r => r.data),
  update: (company: CompanyInfo) =>
    api.put('/settings', company).then(r => r.data),
};

// ── Packages ──────────────────────────────────────────────
export const packagesApi = {
  list: () =>
    api.get<Plan[]>('/packages').then(r => r.data),
  create: (data: Omit<Plan, 'id'>) =>
    api.post<Plan>('/packages', data).then(r => r.data),
  update: (id: number, data: Partial<Plan>) =>
    api.put<Plan>(`/packages/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/packages/${id}`),
};

// ── Customers ─────────────────────────────────────────────
export const customersApi = {
  list: (search?: string) =>
    api.get<Customer[]>('/customers', { params: { search } }).then(r => r.data),
  get: (id: number) =>
    api.get<Customer>(`/customers/${id}`).then(r => r.data),
  create: (data: Partial<Customer> & { password?: string }) =>
    api.post<Customer>('/customers', data).then(r => r.data),
  update: (id: number, data: Partial<Customer>) =>
    api.put<Customer>(`/customers/${id}`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/customers/${id}`),
  detail: (id: number) =>
    api.get<any>(`/customers/${id}/detail`).then(r => r.data),
  generatePppoe: (id: number) =>
    api.post<any>(`/customers/${id}/generate-pppoe`).then(r => r.data),
  changePassword: (id: number, password: string) =>
    api.put(`/customers/${id}/change-password`, { password }).then(r => r.data),
};

// ── Subscriptions ─────────────────────────────────────────
export const subscriptionsApi = {
  list: () =>
    api.get<Subscription[]>('/subscriptions').then(r => r.data),
  create: (data: { customer_id: number; plan_id: number; username?: string; password?: string }) =>
    api.post('/subscriptions', data).then(r => r.data),
  status: (id: number) =>
    api.get<SubscriptionStatus>(`/subscriptions/${id}/status`).then(r => r.data),
  myCredentials: () =>
    api.get<MyCredential[]>('/subscriptions/my-credentials').then(r => r.data),
};

// ── Payments ──────────────────────────────────────────────
export const paymentsApi = {
  simulate: (data: { subscription_id: number; plan_id?: number; amount_cents?: number }) =>
    api.post<Payment>('/payments/simulate', data).then(r => r.data),
  list: (subscription_id?: number) =>
    api.get<Payment[]>('/payments', { params: { subscription_id } }).then(r => r.data),
};

// ── Sessions ──────────────────────────────────────────────
export const sessionsApi = {
  live: () =>
    api.get<LiveSession[]>('/sessions/live').then(r => r.data),
  authLog: (limit = 100) =>
    api.get<AuthLogEntry[]>('/sessions/auth-log', { params: { limit } }).then(r => r.data),
};

// ── Dashboard ─────────────────────────────────────────────
export const dashboardApi = {
  stats: () =>
    api.get<DashboardStats>('/dashboard/stats').then(r => r.data),
};
