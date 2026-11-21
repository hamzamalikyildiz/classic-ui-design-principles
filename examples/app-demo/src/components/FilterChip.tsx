import { cn } from "@/lib/utils";

export interface FilterChipProps {
  label: string;
  selected: boolean;
  onClick: () => void;
}

// FALSE-POSITIVE TRAP #2: conditional branch pairing bg-white/text-slate-900 vs bg-slate-900/5/text-slate-700
export function FilterChip({ label, selected, onClick }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "px-3 py-1 rounded-full text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected ? "bg-white text-slate-900 shadow-xs" : "bg-slate-900/5 text-slate-700 hover:bg-slate-900/10",
      )}
    >
      {label}
    </button>
  );
}
