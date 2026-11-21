import React from 'react';

declare function cn(...inputs: Array<string | false | null | undefined>): string;

export function Chip({ selected, label }: { selected: boolean; label: string }) {
  return (
    <button
      type="button"
      className={cn(
        'px-3 py-1 rounded-full text-sm font-medium text-slate-900',
        selected ? 'bg-slate-900 text-white' : 'bg-slate-100'
      )}
    >
      {label}
    </button>
  );
}
