import type { ScoreBreakdownItem } from "@/types/cv";

const BAR_COLORS = ["bg-teal-400", "bg-emerald-400", "bg-sky-400"];

export interface ScoreBarsProps {
  items: ScoreBreakdownItem[];
}

export function ScoreBars({ items }: ScoreBarsProps) {
  return (
    <div className="mt-4 space-y-3">
      {items.map((item, idx) => (
        <div key={item.label} className="space-y-1">
          <div className="flex items-center justify-between text-sm text-white/85">
            <span>{item.label}</span>
            <span className="font-mono tabular-nums">{item.value}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full w-full rounded-full score-bar-animated ${BAR_COLORS[idx % BAR_COLORS.length]}`}
              style={{ transform: `scaleX(${Math.max(0, Math.min(1, item.value / 100))})` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
