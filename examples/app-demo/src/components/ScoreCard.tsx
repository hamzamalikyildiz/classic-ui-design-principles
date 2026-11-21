import { ScoreBars } from "./ScoreBars";
import type { ScoreBreakdownItem, ScoreRevision } from "@/types/cv";

export interface ScoreCardProps {
  score: number;
  history: ScoreRevision[];
  breakdown: ScoreBreakdownItem[];
}

export function ScoreCard({ score, history, breakdown }: ScoreCardProps) {
  return (
    <section className="rounded-xl bg-slate-900 p-6 text-white shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <p className="text-sm text-slate-300">Güncel Uyumluluk Skoru</p>
          <p className="mt-1 text-4xl font-bold tracking-tight tabular-nums">
            {score}
            <span className="text-lg font-normal text-slate-300"> / 100</span>
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-300">
          {history.map((rev, idx) => (
            <span key={rev.id} className="font-mono tabular-nums">
              {rev.label}: {rev.score}
              {idx < history.length - 1 ? " ->" : ""}
            </span>
          ))}
        </div>
      </div>
      <ScoreBars items={breakdown} />
    </section>
  );
}
