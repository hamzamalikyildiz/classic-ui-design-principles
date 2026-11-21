import React from 'react';

declare function cn(...inputs: Array<string | false | null | undefined>): string;

export function BadContrastCard() {
  return (
    <div className="rounded-lg bg-slate-100 p-4">
      <p className="text-sm text-slate-300">Unreadable muted text on light slate</p>
    </div>
  );
}

export function BadContrastBranch({ active }: { active: boolean }) {
  return (
    <button
      type="button"
      className={cn(
        'px-3 py-1 rounded-full text-sm',
        active ? 'bg-slate-900 text-white' : 'bg-slate-200 text-slate-400'
      )}
    >
      Status
    </button>
  );
}
