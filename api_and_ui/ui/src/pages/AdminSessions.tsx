import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { sessionsApi } from '../services/api';
import Layout from '../components/Layout';
import type { LiveSession, AuthLogEntry } from '../types';

export default function AdminSessions() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<LiveSession[]>([]);
  const [authLog, setAuthLog] = useState<AuthLogEntry[]>([]);
  const [tab, setTab] = useState<'live' | 'log'>('live');

  const load = async () => {
    const [s, l] = await Promise.all([sessionsApi.live(), sessionsApi.authLog(50)]);
    setSessions(s);
    setAuthLog(l);
  };

  useEffect(() => { if (isAdmin) load(); else navigate('/dashboard'); }, [isAdmin, navigate]);

  const formatBytes = (b: number) => b > 1_000_000 ? `${(b / 1_000_000).toFixed(1)} MB` : b > 1000 ? `${(b / 1000).toFixed(1)} KB` : `${b} B`;

  return (
    <Layout admin>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Sessions</h2>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          <button onClick={() => setTab('live')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${tab === 'live' ? 'bg-white shadow' : ''}`}
          >Live ({sessions.length})</button>
          <button onClick={() => setTab('log')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${tab === 'log' ? 'bg-white shadow' : ''}`}
          >Auth Log</button>
        </div>
      </div>

      {tab === 'live' ? (
        <div className="space-y-3">
          {sessions.length === 0 && <p className="text-gray-500 text-center py-8">No active sessions</p>}
          {sessions.map(s => (
            <div key={s.radacct_id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm flex items-center justify-between">
              <div>
                <span className="font-mono text-sm font-semibold">{s.username}</span>
                <p className="text-xs text-gray-500">NAS: {s.nas_ip} | IP: {s.framed_ip || '-'}</p>
              </div>
              <div className="text-right text-xs text-gray-600">
                <p>{Math.floor(s.session_time / 60)}m runtime</p>
                <p>⬇ {formatBytes(s.input_bytes)} ⬆ {formatBytes(s.output_bytes)}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-gray-500">
                <th className="pb-2">Time</th>
                <th className="pb-2">Username</th>
                <th className="pb-2">Result</th>
              </tr>
            </thead>
            <tbody>
              {authLog.map(e => (
                <tr key={e.id} className="border-b last:border-0">
                  <td className="py-2 text-xs text-gray-500">{new Date(e.authdate).toLocaleString()}</td>
                  <td className="py-2 font-mono text-xs">{e.username}</td>
                  <td className="py-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${e.reply === 'Access-Accept' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {e.reply}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button onClick={load} className="mt-4 text-sm text-indigo-600 hover:underline">🔄 Refresh</button>
    </Layout>
  );
}
