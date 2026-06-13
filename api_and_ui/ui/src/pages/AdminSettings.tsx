import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { settingsApi } from '../services/api';
import Layout from '../components/Layout';
import type { CompanyInfo } from '../types';

export default function AdminSettings() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState<CompanyInfo>({
    name: '', short_name: '', tagline: '', currency: '', currency_symbol: '', support_email: '', support_phone: '',
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isAdmin) { navigate('/dashboard'); return; }
    settingsApi.get().then(d => d.company && setCompany(d.company));
  }, [isAdmin, navigate]);

  const handleSave = async () => {
    try {
      await settingsApi.update(company);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to save');
    }
  };

  return (
    <Layout admin>
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">Company Settings</h2>
        <p className="text-sm text-gray-500 mb-4">
          Update your company branding. These values are used across the customer portal and can be changed anytime.
        </p>

        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          {[
            ['Company Name', 'name', company.name],
            ['Short Name', 'short_name', company.short_name],
            ['Tagline', 'tagline', company.tagline],
            ['Currency Code', 'currency', company.currency],
            ['Currency Symbol', 'currency_symbol', company.currency_symbol],
            ['Support Email', 'support_email', company.support_email],
            ['Support Phone', 'support_phone', company.support_phone],
          ].map(([label, key, value]) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                value={value}
                onChange={e => setCompany(c => ({ ...c, [key]: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          ))}

          <div className="flex gap-3 pt-2">
            <button onClick={handleSave}
              className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-700 transition"
            >
              {saved ? '✓ Saved!' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
