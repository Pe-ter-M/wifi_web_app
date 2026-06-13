import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { customersApi, subscriptionsApi, packagesApi } from '../services/api';
import { useToast } from '../components/Toast';
import ConfirmModal from '../components/ConfirmModal';
import Layout from '../components/Layout';
import type { Customer, Plan, Subscription } from '../types';

export default function AdminCustomers() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [customers, setCustomers] = useState<(Customer & { subscriptions?: Subscription[] })[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [detailCust, setDetailCust] = useState<any>(null);
  const [createdResult, setCreatedResult] = useState<any>(null);
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', plan_id: 0 });
  const [errors, setErrors] = useState<string[]>([]);

  // Confirm modals state
  const [confirmDel, setConfirmDel] = useState<number | null>(null);
  const [confirmGen, setConfirmGen] = useState<number | null>(null);

  const load = async (q?: string) => {
    const [custs, pkgList, subs] = await Promise.all([
      customersApi.list(q || undefined),
      packagesApi.list(),
      subscriptionsApi.list(),
    ]);
    const merged = custs.map((c: Customer) => ({
      ...c,
      subscriptions: (subs as any[]).filter((s: any) => s.customer_id === c.id),
    }));
    setCustomers(merged);
    setPlans(pkgList.filter((p: Plan) => p.is_active));
  };

  useEffect(() => { if (isAdmin) load(); else navigate('/dashboard'); }, [isAdmin, navigate]);

  const validate = () => {
    const errs: string[] = [];
    if (!form.name.trim()) errs.push('Name is required');
    if (!form.email.trim()) errs.push('Email is required');
    if (!form.phone.trim()) errs.push('Phone is required');
    if (!form.password || form.password.length < 4) errs.push('Password is required (min 4 chars)');
    setErrors(errs);
    return errs.length === 0;
  };

  const handleCreate = async () => {
    if (!validate()) return;
    try {
      const cust = await customersApi.create({ name: form.name, email: form.email, phone: form.phone, password: form.password });
      let subResult = null;
      if (form.plan_id > 0) {
        subResult = await subscriptionsApi.create({ customer_id: cust.id, plan_id: form.plan_id });
      }
      setCreatedResult({ customer: cust, subscription: subResult });
      setShowModal(false);
      setForm({ name: '', email: '', phone: '', password: '', plan_id: 0 });
      setErrors([]);
      addToast('success', `Customer ${cust.name} created successfully`);
      load();
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to create customer');
    }
  };

  const handleDelete = async () => {
    if (confirmDel === null) return;
    try {
      await customersApi.delete(confirmDel);
      addToast('success', 'Customer deleted and RADIUS access revoked');
      setConfirmDel(null);
      load();
      if (detailCust?.customer?.id === confirmDel) setDetailCust(null);
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to delete');
      setConfirmDel(null);
    }
  };

  const handleViewDetail = async (id: number) => {
    try {
      const data = await customersApi.detail(id);
      setDetailCust(data);
    } catch {
      addToast('error', 'Failed to load customer details');
    }
  };

  const handleGeneratePppoe = async () => {
    if (confirmGen === null) return;
    try {
      const result = await customersApi.generatePppoe(confirmGen);
      addToast('success', `PPPoE generated: ${result.username}`);
      setConfirmGen(null);
      handleViewDetail(confirmGen);
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to generate PPPoE');
      setConfirmGen(null);
    }
  };

  const handleGenerateClick = (id: number) => {
    // Check if customer already has an active subscription
    const cust = customers.find(c => c.id === id);
    if (cust?.subscriptions && cust.subscriptions.length > 0) {
      setConfirmGen(id);
    } else {
      // No existing sub — generate directly
      setConfirmGen(id);
    }
  };

  return (
    <Layout admin>
      {/* Confirm modals */}
      <ConfirmModal
        open={confirmDel !== null}
        title="Delete Customer?"
        message="This will remove the customer and revoke their RADIUS internet access immediately."
        confirmLabel="Delete"
        variant="danger"
        icon="🗑"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDel(null)}
      />

      <ConfirmModal
        open={confirmGen !== null}
        title="Generate New PPPoE?"
        message="This customer already has an active subscription. A new one will be created as a 1-hour trial. Proceed?"
        confirmLabel="Generate"
        variant="primary"
        icon="🔑"
        onConfirm={handleGeneratePppoe}
        onCancel={() => setConfirmGen(null)}
      />

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Customers</h2>
        <div className="flex gap-3">
          <input type="text" placeholder="Search..." value={search}
            onChange={e => { setSearch(e.target.value); load(e.target.value); }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
          <button onClick={() => { setCreatedResult(null); setErrors([]); setShowModal(true); }}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">+ Add Customer</button>
        </div>
      </div>

      {/* Created credentials popup */}
      {createdResult && (
        <div className="bg-green-50 border-2 border-green-400 rounded-xl p-5 mb-6 shadow-md">
          <div className="flex items-start justify-between">
            <h3 className="text-lg font-bold text-green-800">✅ Customer Created</h3>
            <button onClick={() => setCreatedResult(null)} className="text-green-600 text-xl hover:text-green-800">&times;</button>
          </div>
          <p className="text-sm text-green-700 mt-1">{createdResult.customer?.name} &lt;{createdResult.customer?.email}&gt;</p>
          {createdResult.subscription && (
            <div className="mt-3 bg-white rounded-lg p-3 border border-green-200">
              <p className="font-semibold text-sm text-gray-700 mb-1">🔑 PPPoE Credentials (1-hour trial)</p>
              <table className="text-sm w-full">
                <tbody>
                  <tr><td className="text-gray-500 pr-4 py-1">Username</td><td className="font-mono font-bold">{createdResult.subscription.username}</td></tr>
                  <tr><td className="text-gray-500 pr-4 py-1">Password</td><td className="font-mono font-bold">{createdResult.subscription.password}</td></tr>
                  <tr><td className="text-gray-500 pr-4 py-1">Plan</td><td>{createdResult.subscription.plan}</td></tr>
                  <tr><td className="text-gray-500 pr-4 py-1">Expires (trial)</td><td>{new Date(createdResult.subscription.expires_at).toLocaleString()}</td></tr>
                </tbody>
              </table>
              <p className="text-xs text-amber-600 mt-2">⚠️ Copy these — they won't be shown again after closing.</p>
            </div>
          )}
          {!createdResult.subscription && (
            <p className="text-sm text-gray-500 mt-2">No plan assigned. Click "Generate PPPoE" later.</p>
          )}
        </div>
      )}

      {/* Customer list */}
      <div className="space-y-3">
        {customers.map(c => (
          <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow transition cursor-pointer"
               onClick={() => handleViewDetail(c.id)}>
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-indigo-700 hover:underline">{c.name}</h3>
                <p className="text-sm text-gray-500 truncate">{c.email} {c.phone && `| ${c.phone}`}</p>
              </div>
              <div className="flex items-center gap-2 ml-3 shrink-0">
                <button onClick={e => { e.stopPropagation(); handleViewDetail(c.id); }}
                  className="text-xs bg-indigo-50 text-indigo-600 border border-indigo-200 px-3 py-1.5 rounded-lg hover:bg-indigo-100 font-medium transition">
                  Details
                </button>
                <button onClick={e => { e.stopPropagation(); setConfirmDel(c.id); }}
                  className="text-xs text-red-500 border border-red-200 px-3 py-1.5 rounded-lg hover:bg-red-50 transition">
                  Delete
                </button>
              </div>
            </div>
            {c.subscriptions && c.subscriptions.length > 0 ? (
              <div className="mt-2 space-y-1">
                {c.subscriptions.map(s => (
                  <div key={s.id} className="flex items-center gap-2 text-xs">
                    <span className={`px-2 py-0.5 rounded-full font-medium ${
                      s.status === 'active' ? 'bg-green-100 text-green-700' :
                      s.status === 'trial' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {s.status === 'trial' ? 'TRIAL' : s.status.toUpperCase()}
                    </span>
                    <span className="font-mono font-semibold">{s.username}</span>
                    <span className="text-gray-400">
                      {s.status === 'trial'
                        ? `trial ends ${new Date(s.current_period_end).toLocaleString()}`
                        : `exp: ${new Date(s.current_period_end).toLocaleDateString()}`
                      }
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 mt-2">No subscriptions</p>
            )}
          </div>
        ))}
      </div>

      {/* Detail slide-over */}
      {detailCust && (
        <div className="fixed inset-0 bg-black/30 z-50 flex justify-end" onClick={() => setDetailCust(null)}>
          <div className="bg-white w-full max-w-lg h-full overflow-y-auto shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <h3 className="text-xl font-bold">Customer Details</h3>
                <button onClick={() => setDetailCust(null)} className="text-2xl text-gray-400 hover:text-gray-600">&times;</button>
              </div>

              <div className="bg-gray-50 rounded-xl p-4 mb-4">
                <h4 className="font-semibold text-sm text-gray-600 mb-2">Account Info</h4>
                <table className="text-sm w-full">
                  <tbody>
                    <tr><td className="text-gray-500 pr-4 py-1">ID</td><td className="font-semibold">#{detailCust.customer.id}</td></tr>
                    <tr><td className="text-gray-500 pr-4 py-1">Name</td><td className="font-semibold">{detailCust.customer.name}</td></tr>
                    <tr><td className="text-gray-500 pr-4 py-1">Email</td><td>{detailCust.customer.email}</td></tr>
                    <tr><td className="text-gray-500 pr-4 py-1">Phone</td><td>{detailCust.customer.phone || '-'}</td></tr>
                    <tr><td className="text-gray-500 pr-4 py-1">Address</td><td>{detailCust.customer.address || '-'}</td></tr>
                    <tr><td className="text-gray-500 pr-4 py-1">Created</td><td>{detailCust.customer.created_at ? new Date(detailCust.customer.created_at).toLocaleString() : '-'}</td></tr>
                  </tbody>
                </table>
              </div>

              <div className="flex gap-2 mb-4">
                <button onClick={() => handleGenerateClick(detailCust.customer.id)}
                  className="bg-amber-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-amber-600 transition">
                  + Generate PPPoE
                </button>
                <button onClick={() => setConfirmDel(detailCust.customer.id)}
                  className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-600 transition">
                  Delete Customer
                </button>
              </div>

              <h4 className="font-semibold text-sm text-gray-600 mb-2">Subscriptions ({detailCust.subscriptions.length})</h4>
              {detailCust.subscriptions.length === 0 && (
                <div className="bg-gray-50 rounded-xl p-6 text-center">
                  <p className="text-sm text-gray-400 mb-2">No subscriptions yet</p>
                  <button onClick={() => handleGenerateClick(detailCust.customer.id)}
                    className="bg-amber-500 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-amber-600 transition">
                    + Generate One-Time PPPoE
                  </button>
                </div>
              )}
              {detailCust.subscriptions.map((s: any) => (
                <div key={s.id} className={`rounded-xl p-4 mb-3 border-2 ${
                  s.is_active
                    ? s.is_trial ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'
                    : 'border-red-200 bg-red-50'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                      s.is_active
                        ? s.is_trial ? 'bg-amber-200 text-amber-800' : 'bg-green-200 text-green-800'
                        : 'bg-red-200 text-red-800'
                    }`}>
                      {s.is_active ? (s.is_trial ? '● TRIAL' : '● ONLINE') : '● OFFLINE'}
                    </span>
                    <span className="text-xs text-gray-500">#{s.id}</span>
                  </div>
                  <table className="text-xs w-full">
                    <tbody>
                      <tr><td className="text-gray-500 pr-2 py-1">PPPoE Username</td><td className="font-mono font-bold">{s.username}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">PPPoE Password</td><td className="font-mono font-bold">{s.password}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Plan</td><td>{s.plan_name}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Bandwidth</td><td>{s.bandwidth}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Status</td><td className="capitalize font-medium">{s.status}{s.is_trial ? ' (1h trial)' : ''}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Expires</td><td>{s.current_period_end ? new Date(s.current_period_end).toLocaleString() : '-'}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Days Left</td><td className={s.days_remaining <= 3 ? 'text-red-600 font-bold' : ''}>{s.days_remaining}</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Devices</td><td>{s.device_count} / 1</td></tr>
                      <tr><td className="text-gray-500 pr-2 py-1">Last Seen</td><td>{s.last_seen ? new Date(s.last_seen).toLocaleString() : 'Never'}</td></tr>
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-2">Add Customer</h3>
            <p className="text-xs text-gray-400 mb-3">All fields marked * are required.</p>

            {errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-3">
                {errors.map((e, i) => <p key={i} className="text-xs text-red-600">• {e}</p>)}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 font-medium">Name *</label>
                <input placeholder="Full name" value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">Email *</label>
                <input placeholder="email@example.com" type="email" value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">Phone *</label>
                <input placeholder="+254 7XX XXX XXX" value={form.phone}
                  onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">Portal Password *</label>
                <input placeholder="Min 4 characters" type="text" value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-xs text-gray-500 font-medium">Plan (optional)</label>
                <select value={form.plan_id}
                  onChange={e => setForm(f => ({ ...f, plan_id: Number(e.target.value) }))}
                  className="w-full px-3 py-2 border rounded-lg text-sm">
                  <option value={0}>No plan — generate PPPoE later (1h trial)</option>
                  {plans.map(p => <option key={p.id} value={p.id}>{p.name} — KSh {p.price_display} (1h trial)</option>)}
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button onClick={handleCreate}
                  className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold text-sm hover:bg-indigo-700 transition">Create Customer</button>
                <button onClick={() => setShowModal(false)}
                  className="px-4 py-2 border rounded-lg text-sm">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
