import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { packagesApi } from '../services/api';
import { useToast } from '../components/Toast';
import ConfirmModal from '../components/ConfirmModal';
import Layout from '../components/Layout';
import type { Plan } from '../types';

function TooltipIcon({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block ml-1">
      <span
        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-200 text-gray-500 text-[10px] font-bold cursor-help hover:bg-indigo-200 hover:text-indigo-700 transition"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >?</span>
      {show && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded-lg shadow-lg w-48 text-center pointer-events-none">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-800" />
        </div>
      )}
    </span>
  );
}

export default function AdminPackages() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [confirmDel, setConfirmDel] = useState<number | null>(null);
  // ⚠️ Changed: price field (not price_cents/price_display), added simultaneous_use
  const [form, setForm] = useState({
    name: '', description: '', price: 0,
    bandwidth_up: 8192, bandwidth_down: 8192, session_timeout: 86400,
    idle_timeout: 600, simultaneous_use: 1, is_active: true, sort_order: 0,
  });

  const load = async () => { const p = await packagesApi.list(); setPlans(p); };
  useEffect(() => { if (isAdmin) load(); else navigate('/dashboard'); }, [isAdmin, navigate]);

  const resetForm = () => setForm({
    name: '', description: '', price: 0,
    bandwidth_up: 8192, bandwidth_down: 8192, session_timeout: 86400,
    idle_timeout: 600, simultaneous_use: 1, is_active: true, sort_order: 0,
  });

  const openCreate = () => { setEditId(null); resetForm(); setShowModal(true); };
  const openEdit = (p: Plan) => {
    setEditId(p.id);
    setForm({
      name: p.name, description: p.description || '', price: p.price,
      bandwidth_up: p.bandwidth_up, bandwidth_down: p.bandwidth_down,
      session_timeout: p.session_timeout, idle_timeout: p.idle_timeout,
      simultaneous_use: p.simultaneous_use || 1, is_active: p.is_active, sort_order: p.sort_order,
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    try {
      if (editId) await packagesApi.update(editId, form as any);
      else await packagesApi.create(form as any);
      setShowModal(false);
      addToast('success', editId ? 'Package updated' : 'Package created');
      load();
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Failed to save');
    }
  };

  const handleToggle = async (p: Plan) => {
    await packagesApi.update(p.id, { is_active: !p.is_active });
    addToast('info', `${p.name} ${p.is_active ? 'disabled' : 'enabled'}`);
    load();
  };

  const handleDelete = async () => {
    if (confirmDel === null) return;
    try {
      await packagesApi.delete(confirmDel);
      addToast('success', 'Package deleted');
      setConfirmDel(null);
      load();
    } catch (err: any) {
      addToast('error', err?.response?.data?.detail || 'Cannot delete — may have active subscriptions');
      setConfirmDel(null);
    }
  };

  return (
    <Layout admin>
      <ConfirmModal
        open={confirmDel !== null}
        title="Delete Package?"
        message="This will remove the package. If customers are using it, deactivate it instead."
        confirmLabel="Delete"
        variant="danger"
        icon="📦"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDel(null)}
      />

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Internet Packages</h2>
        <button onClick={openCreate}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition">+ Add Package</button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {plans.map(p => (
          <div key={p.id} className={`bg-white border rounded-xl p-5 shadow-sm ${p.is_active ? 'border-gray-200' : 'border-red-200 opacity-60'}`}>
            <div className="flex items-start justify-between">
              <h3 className="font-bold text-lg">{p.name}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${p.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                {p.is_active ? 'Active' : 'Disabled'}
              </span>
            </div>
            <p className="text-2xl font-extrabold text-indigo-600 mt-1">
              KSh {p.price}<span className="text-xs font-normal text-gray-400">/mo</span>
            </p>
            {p.description && <p className="text-sm text-gray-500 mt-1">{p.description}</p>}
            <div className="text-xs text-gray-600 mt-2">
              {Math.round(p.bandwidth_down / 1024)} Mbps | {p.simultaneous_use} device{p.simultaneous_use > 1 ? 's' : ''} | Timeout: {p.session_timeout}s
            </div>
            <div className="flex gap-2 mt-3">
              <button onClick={() => openEdit(p)} className="text-xs bg-gray-100 px-2 py-1 rounded hover:bg-gray-200 transition">✏ Edit</button>
              <button onClick={() => handleToggle(p)} className="text-xs bg-gray-100 px-2 py-1 rounded hover:bg-gray-200 transition">
                {p.is_active ? '⏸ Disable' : '▶ Enable'}
              </button>
              <button onClick={() => setConfirmDel(p.id)} className="text-xs text-red-500 px-2 py-1 rounded hover:bg-red-50 transition">🗑</button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-4">{editId ? 'Edit Package' : 'Add Package'}</h3>
            <p className="text-xs text-gray-400 mb-3">Hover the <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-200 text-gray-500 text-[10px] font-bold mx-1">?</span> icons for field explanations.</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div><label className="text-xs text-gray-500">Name<TooltipIcon text="Package name shown to customers" /></label><input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Description</label><input value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Price (KSh)<TooltipIcon text="Monthly price e.g. 1500" /></label><input type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Max Devices<TooltipIcon text="Simultaneous connections allowed" /></label><input type="number" value={form.simultaneous_use} onChange={e => setForm(f => ({ ...f, simultaneous_use: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Download (Kbps)<TooltipIcon text="10240 = 10 Mbps" /></label><input type="number" value={form.bandwidth_down} onChange={e => setForm(f => ({ ...f, bandwidth_down: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Upload (Kbps)</label><input type="number" value={form.bandwidth_up} onChange={e => setForm(f => ({ ...f, bandwidth_up: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Session Timeout (s)<TooltipIcon text="86400s = 24 hours" /></label><input type="number" value={form.session_timeout} onChange={e => setForm(f => ({ ...f, session_timeout: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="text-xs text-gray-500">Idle Timeout (s)</label><input type="number" value={form.idle_timeout} onChange={e => setForm(f => ({ ...f, idle_timeout: Number(e.target.value) }))} className="w-full px-3 py-2 border rounded-lg" /></div>
              <label className="flex items-center gap-2 text-sm mt-2 col-span-2">
                <input type="checkbox" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
                Active (visible to customers)
              </label>
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={handleSave} className="flex-1 bg-indigo-600 text-white py-2 rounded-lg font-semibold hover:bg-indigo-700 transition">Save</button>
              <button onClick={() => setShowModal(false)} className="px-4 py-2 border rounded-lg">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}