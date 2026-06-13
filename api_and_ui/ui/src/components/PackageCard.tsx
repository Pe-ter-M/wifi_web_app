import React from 'react';
import type { Plan } from '../types';

interface Props {
  plan: Plan;
  selected?: boolean;
  onSelect?: () => void;
  currencySymbol?: string;
}

export default function PackageCard({ plan, selected, onSelect, currencySymbol = 'KSh' }: Props) {
  const mbps = Math.round((plan.bandwidth_down || 8192) / 1024);
  return (
    <div
      onClick={onSelect}
      className={`p-5 rounded-xl border-2 cursor-pointer transition-all ${
        selected
          ? 'border-indigo-500 bg-indigo-50 shadow-md scale-[1.02]'
          : 'border-gray-200 bg-white hover:border-indigo-300 hover:shadow'
      }`}
    >
      <h3 className="text-lg font-bold text-gray-800">{plan.name}</h3>
      <p className="text-2xl font-extrabold text-indigo-600 mt-1">
        {currencySymbol} {plan.price_display ?? (plan.price_cents / 100).toFixed(0)}
        <span className="text-sm font-normal text-gray-400">/mo</span>
      </p>
      {plan.description && (
        <p className="text-sm text-gray-500 mt-1">{plan.description}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-600">
        <span className="bg-gray-100 px-2 py-1 rounded">⬇ {mbps} Mbps</span>
        <span className="bg-gray-100 px-2 py-1 rounded">⬆ {mbps} Mbps</span>
        <span className="bg-gray-100 px-2 py-1 rounded">1 device</span>
      </div>
    </div>
  );
}
