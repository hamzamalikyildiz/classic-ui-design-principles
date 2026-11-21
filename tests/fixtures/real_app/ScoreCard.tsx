import React from 'react';

function ScoreBars() {
  return (
    <div className="mt-4 space-y-2">
      <div className="flex items-center justify-between text-sm text-white/80">
        <span>Accessibility</span>
        <span>92%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-white/10">
        <div className="h-2 w-11/12 rounded-full bg-emerald-400" />
      </div>
    </div>
  );
}

export function ScoreCard() {
  return (
    <section className="rounded-xl bg-slate-900 p-6 text-white">
      <h2 className="text-lg font-semibold">Quality Score</h2>
      <p className="mt-1 text-sm text-slate-300">Automated audit summary</p>
      <ScoreBars />
    </section>
  );
}
