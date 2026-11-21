import React from 'react';

export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8 bg-white">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-slate-600">Overview of account metrics and recent activity.</p>
      </header>
      <section className="grid grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6">
          <h2 className="text-lg font-semibold text-slate-900">Revenue</h2>
          <p className="mt-2 text-2xl font-bold text-slate-900">$12,480</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6">
          <h2 className="text-lg font-semibold text-slate-900">Active Users</h2>
          <p className="mt-2 text-2xl font-bold text-slate-900">1,284</p>
        </div>
      </section>
    </main>
  );
}
