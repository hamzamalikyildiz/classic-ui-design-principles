import type { ScoreBreakdownItem } from "@/types/cv";

const BAR_COLORS = ["bg-teal-400", "bg-emerald-400", "bg-sky-400"];

export interface ScoreBarsProps {
  items: ScoreBreakdownItem[];
}

// FALSE-POSITIVE TRAP #1: text-white/80 inside parent ScoreCard (bg-slate-900)
export function ScoreBars({ items }: ScoreBarsProps) {
  return (
    <div className="mt-4 space-y-3">
      {items.map((item, idx) => (
        <div key={item.label} className="space-y-1">
          <div className="flex items-center justify-between text-sm text-white/80">
            <span>{item.label}</span>
            <span className="font-mono tabular-nums">{item.value}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            {/* DELIBERATE DEFECT #6: layout-property transition on width/height */}
            <div
              className={`h-full rounded-full score-bar-animated ${BAR_COLORS[idx % BAR_COLORS.length]}`}
              style={{ width: `${item.value}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
