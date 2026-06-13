import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import type { CompanyInfo } from '../types';

export default function Layout({ children, admin }: { children: React.ReactNode; admin?: boolean }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [company, setCompany] = useState<CompanyInfo>({ name: 'Phantom Internet Providers', short_name: 'PhantomNet', tagline: '', currency: 'KSH', currency_symbol: 'KSh', support_email: '', support_phone: '' });

  useEffect(() => {
    settingsApi.get().then(d => d.company && setCompany(d.company)).catch(() => {});
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-indigo-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to={isAdmin ? '/admin' : '/dashboard'} className="text-xl font-bold tracking-tight">
              ⚡ {company.short_name || company.name}
            </Link>
            {admin && (
              <span className="text-xs bg-indigo-500 px-2 py-0.5 rounded-full">Admin</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {user && (
              <>
                <span className="text-sm hidden sm:inline">{user.name}</span>
                <button onClick={handleLogout} className="text-sm bg-indigo-600 hover:bg-indigo-500 px-3 py-1 rounded-lg transition">
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
        {/* Admin nav */}
        {admin && (
          <nav className="bg-indigo-800">
            <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
              {[
                ['Dashboard', '/admin'],
                ['Customers', '/admin/customers'],
                ['Packages', '/admin/packages'],
                ['Sessions', '/admin/sessions'],
                ['Settings', '/admin/settings'],
              ].map(([label, path]) => (
                <Link key={path} to={path}
                  className="px-4 py-2 text-sm hover:bg-indigo-600 rounded-t-lg transition whitespace-nowrap"
                >{label}</Link>
              ))}
            </div>
          </nav>
        )}
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 text-center text-xs text-gray-500 py-4 border-t">
        {company.name} &copy; {new Date().getFullYear()} &mdash; Powered by PhantomNet
      </footer>
    </div>
  );
}
