import React from 'react';

interface Props {
  isActive: boolean;
  label?: string;
}

export default function StatusIndicator({ isActive, label }: Props) {
  return (
    <div className="flex items-center gap-2">
      <span className={`w-4 h-4 rounded-full ${isActive ? 'bg-green-500 status-dot-active' : 'bg-red-500 status-dot-expired'}`} />
      <span className={`text-sm font-semibold ${isActive ? 'text-green-700' : 'text-red-700'}`}>
        {label || (isActive ? 'Active' : 'Expired')}
      </span>
    </div>
  );
}
