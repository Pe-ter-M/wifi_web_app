import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { dashboardApi, subscriptionsApi, customersApi } from '../services/api';
import Layout from '../components/Layout';
import type { DashboardStats } from '../types';

export default function AdminDashboard() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    if (!isAdmin) { navigate('/dashboard'); return; }
    dashboardApi.stats().then(setStats).catch(console.error);
  }, [isAdmin, navigate]);

  const formatKSH = (amount: number) => `KSh ${(amount || 0).toLocaleString()}`;
  const fmt = (n: number | undefined) => n?.toLocaleString() ?? '-';

  return (
    <Layout admin>
      <h2 className="text-2xl font-bold mb-6">Admin Dashboard</h2>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {[
          ['📊', 'Total Customers', fmt(stats?.total_customers)],
          ['✅', 'Active Subs', fmt(stats?.active_subscriptions)],
          ['⚠️', 'Expired Subs', fmt(stats?.expired_subscriptions)],
          ['🔗', 'Live Sessions', fmt(stats?.live_sessions)],
          ['💰', 'Revenue Today', stats ? formatKSH(stats.revenue_today) : '-'],
          ['💵', 'Revenue This Month', stats ? formatKSH(stats.revenue_this_month) : '-'],
        ].map(([icon, label, value]) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
            <span className="text-2xl">{icon}</span>
            <p className="text-sm text-gray-500 mt-2">{label}</p>
            <p className="text-2xl font-bold">{value}</p>
          </div>
        ))}
      </div>

      {/* Recent subscriptions */}
      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <Link to="/admin/customers" className="bg-indigo-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-indigo-700">
            + Add Customer
          </Link>
          <Link to="/admin/packages" className="bg-white border border-gray-300 px-5 py-2.5 rounded-lg font-medium hover:bg-gray-50">
            Manage Packages
          </Link>
          <Link to="/admin/sessions" className="bg-white border border-gray-300 px-5 py-2.5 rounded-lg font-medium hover:bg-gray-50">
            View Live Sessions
          </Link>
        </div>
      </div>
    </Layout>
  );
}
