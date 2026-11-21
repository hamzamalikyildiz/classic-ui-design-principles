import { useEffect, useState } from "react";
import { ScoreBars } from "./ScoreBars";
import type { ScoreBreakdownItem, ScoreRevision } from "@/types/cv";

export interface ScoreCardProps {
  score: number;
  history: ScoreRevision[];
  breakdown: ScoreBreakdownItem[];
}

export function ScoreCard({ score, history, breakdown }: ScoreCardProps) {
  const [displayScore, setDisplayScore] = useState(score);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setDisplayScore(score);
      return;
    }

    const start = Math.max(0, score - 6);
    const duration = 450;
    const t0 = performance.now();
    let raf = 0;

    function tick(now: number) {
      const progress = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(start + (score - start) * eased));
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    }

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (Math.max(0, Math.min(100, displayScore)) / 100) * circumference;

  return (
    <section className="rounded-xl bg-slate-900 p-6 text-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <svg
            width="84"
            height="84"
            viewBox="0 0 84 84"
            className="shrink-0 -rotate-90"
            aria-hidden="true"
          >
            <circle
              cx="42"
              cy="42"
              r={radius}
              fill="none"
              stroke="rgb(51 65 85)"
              strokeWidth="8"
            />
            <circle
              cx="42"
              cy="42"
              r={radius}
              fill="none"
              stroke="rgb(45 212 191)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              className="ring-fg"
            />
          </svg>
          <div>
            <p className="text-sm text-slate-300">Güncel Uyumluluk Skoru</p>
            <p
              aria-live="polite"
              className="mt-1 text-4xl font-bold tracking-tight tabular-nums"
            >
              {displayScore}
              <span className="text-lg font-normal text-slate-300"> / 100</span>
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
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
