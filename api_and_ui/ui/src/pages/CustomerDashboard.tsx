import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { subscriptionsApi, settingsApi, customersApi } from '../services/api';
import Layout from '../components/Layout';
import StatusIndicator from '../components/StatusIndicator';
import type { MyCredential, CompanyInfo } from '../types';

function Countdown({ expiresAt }: { expiresAt: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const target = new Date(expiresAt).getTime();
  const diff = Math.max(0, Math.floor((target - now) / 1000));
  const d = Math.floor(diff / 86400);
  const h = Math.floor((diff % 86400) / 3600);
  const m = Math.floor((diff % 3600) / 60);
  const s = diff % 60;

  return (
    <span className="font-mono font-bold text-sm tabular-nums">
      {d > 0 ? `${d}d ` : ''}{String(h).padStart(2, '0')}h {String(m).padStart(2, '0')}m {String(s).padStart(2, '0')}s
    </span>
  );
}

export default function CustomerDashboard() {
  const { user, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [creds, setCreds] = useState<MyCredential[]>([]);
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPw, setShowPw] = useState(false);
  const [pwForm, setPwForm] = useState({ show: false, old: '', new1: '', new2: '' });
  const [pwMsg, setPwMsg] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!user) return;
    if (isAdmin) { navigate('/admin'); return; }
    const load = async () => {
      try {
        const [comp, credentials] = await Promise.all([
          settingsApi.get(),
          subscriptionsApi.myCredentials(),
        ]);
        setCompany(comp.company);
        setCreds(credentials);
      } catch (err) {
        console.error('Failed to load dashboard', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user, isAdmin, navigate, refreshKey]);

  useEffect(() => {
    const id = setInterval(() => setRefreshKey(k => k + 1), 30000);
    return () => clearInterval(id);
  }, []);

  const handleChangePw = async () => {
    if (pwForm.new1 !== pwForm.new2) { setPwMsg('Passwords do not match'); return; }
    if (pwForm.new1.length < 4) { setPwMsg('Password must be at least 4 characters'); return; }
    try {
      await customersApi.changePassword(user!.customer_id, pwForm.new1);
      setPwMsg('✅ Password changed!');
      setPwForm({ show: false, old: '', new1: '', new2: '' });
      setTimeout(() => setPwMsg(''), 3000);
    } catch (err: any) {
      setPwMsg(err?.response?.data?.detail || 'Failed');
    }
  };

  if (loading) return <Layout><div className="text-center py-12 text-gray-500">Loading...</div></Layout>;

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold">Welcome, {user?.name}</h2>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
          <button onClick={() => setPwForm(f => ({ ...f, show: !f.show }))}
            className="text-sm text-indigo-600 border border-indigo-300 px-3 py-1.5 rounded-lg hover:bg-indigo-50">
            Change Portal Password
          </button>
          <StatusIndicator isActive={creds.some(c => c.is_active)}
            label={creds.some(c => c.is_active) ? 'Internet Active' : 'Internet Cut Off'} />
        </div>

        {pwForm.show && (
          <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
            <h3 className="font-semibold mb-2">Change Portal Password</h3>
            <div className="flex flex-wrap gap-2 items-end">
              <div>
                <label className="text-xs text-gray-500">New Password</label>
                <input type="text" value={pwForm.new1} onChange={e => setPwForm(f => ({ ...f, new1: e.target.value }))}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" placeholder="min 4 chars" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Confirm</label>
                <input type="text" value={pwForm.new2} onChange={e => setPwForm(f => ({ ...f, new2: e.target.value }))}
                  className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm" placeholder="repeat" />
              </div>
              <button onClick={handleChangePw} className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-semibold">Save</button>
            </div>
            {pwMsg && <p className="text-sm mt-2 text-green-600">{pwMsg}</p>}
          </div>
        )}

        {creds.length === 0 && (
          <div className="bg-yellow-50 border-2 border-yellow-300 rounded-xl p-6 text-center">
            <p className="text-yellow-800">No subscriptions found. Contact support.</p>
          </div>
        )}

        {creds.map(c => (
          <div key={c.id} className={`rounded-xl p-6 border-2 ${c.is_active ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'}`}>
            <div className="flex items-start justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-lg font-semibold">
                  {c.is_active ? '✅ Internet Active' : '❌ Internet Cut Off'}
                </h3>
                <p className="text-sm text-gray-600">
                  {c.is_active ? 'Connection active — ' : 'Subscription expired. Make a payment to reconnect.'}
                  {c.is_active && c.expires_at && <Countdown expiresAt={c.expires_at} />}
                </p>
              </div>
              <StatusIndicator isActive={c.is_active} label={c.is_active ? 'Online' : 'Offline'} />
            </div>

            <div className="mt-4 bg-white/70 rounded-lg p-4 border border-gray-200">
              <h4 className="font-semibold text-sm text-gray-700 mb-2">🔑 PPPoE Connection Details</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 rounded p-2.5">
                  <span className="text-gray-500 text-xs">Username</span>
                  <p className="font-mono font-bold text-base select-all">{c.username}</p>
                </div>
                <div className="bg-gray-50 rounded p-2.5">
                  <span className="text-gray-500 text-xs">Password</span>
                  <p className="font-mono font-bold text-base select-all">
                    {showPw ? c.password : '••••••••••'}
                    <button onClick={() => setShowPw(!showPw)} className="ml-2 text-xs text-indigo-500 hover:underline">
                      {showPw ? 'Hide' : 'Show'}
                    </button>
                  </p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Plan</span>
                  <p className="font-semibold">{c.plan_name} — {company?.currency_symbol} {c.price ?? 0}/mo</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Status</span>
                  <p className="font-semibold capitalize">{c.status}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Time Remaining</span>
                  <p className="font-semibold text-base">{c.expires_at && <Countdown expiresAt={c.expires_at} />}</p>
                </div>
                <div>
                  <span className="text-gray-500 text-xs">Devices Connected</span>
                  <p className="font-semibold">{c.device_count} / {c.max_devices}</p>
                </div>
                {c.last_seen && (
                  <div className="col-span-2">
                    <span className="text-gray-500 text-xs">Last Seen</span>
                    <p className="font-semibold">{new Date(c.last_seen).toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <Link to="/payment"
                className="flex-1 bg-indigo-600 text-white text-center py-3 rounded-xl font-semibold hover:bg-indigo-700 transition">
                {c.is_active ? 'Renew / Upgrade Plan' : 'Pay to Reconnect'}
              </Link>
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}