import React from 'react';

export function Sidebar() {
  return (
    <aside className="w-64 border-r border-slate-200 bg-white p-4">
      <nav className="space-y-2">
        <a href="/dashboard" className="block rounded-md px-3 py-2 text-slate-700">
          Dashboard
        </a>
        <a href="/reports" className="block rounded-md px-3 py-2 text-slate-700">
          Reports
        </a>
        <a href="/settings" className="block rounded-md px-3 py-2 text-slate-700">
          Settings
        </a>
      </nav>
    </aside>
  );
}
