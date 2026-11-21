import { useEffect, useState } from "react";
import { Bell, CheckCircle2, Circle, Loader2, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface LongOperationStage {
  id: string;
  label: string;
  detail: string;
}

const DEFAULT_STAGES: LongOperationStage[] = [
  { id: "parse", label: "CV ayrıştırılıyor", detail: "Başlık, deneyim tarihleri ve yetkinlikler çıkarılıyor" },
  { id: "match", label: "Deneyim eşleştiriliyor", detail: "Rol gereksinimleri ve etki metrikleri kıyaslanıyor" },
  { id: "suggest", label: "Etki önerileri yazılıyor", detail: "Skor artırıcı somut cümleler hazırlanıyor" },
];

export interface LongOperationPanelProps {
  title?: string;
  subtitle?: string;
  stages?: LongOperationStage[];
  previewTags?: string[];
  onCancel?: () => void;
  onBackground?: () => void;
  failedStep?: number | null;
  onRetryStep?: (stepIndex: number) => void;
}

export function LongOperationPanel({
  title = "AI Uyumluluk Analizi Çalışıyor",
  subtitle = "Bu işlem birkaç aşamadan oluşur; ara sonuçlar hazır oldukça aşağıda görünür.",
  stages = DEFAULT_STAGES,
  previewTags = ["Design Systems", "OKLCH Tokens", "React 19", "A11y"],
  onCancel,
  onBackground,
  failedStep = null,
  onRetryStep,
}: LongOperationPanelProps) {
  const [elapsed, setElapsed] = useState(1);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const activeIndex = failedStep !== null ? failedStep : Math.min(stages.length - 1, Math.floor(elapsed / 3));
  const progressPct = failedStep !== null ? Math.round(((failedStep + 1) / stages.length) * 100) : Math.min(96, 20 + elapsed * 8);
  const pastUpperBound = elapsed > 60;

  return (
    <Card className="mx-auto w-full max-w-2xl">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{title}</CardTitle>
          <span
            aria-live="polite"
            className="rounded-md bg-muted px-2.5 py-1 font-mono text-xs font-medium text-foreground tabular-nums"
          >
            {pastUpperBound
              ? `Geçen ${elapsed} sn · Sonuçlandırılıyor...`
              : `Geçen ${elapsed} sn · Genellikle 30–60 sn`}
          </span>
        </div>
        <CardDescription>{subtitle}</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
            <span aria-live="polite">
              {failedStep !== null
                ? `Adım ${failedStep + 1} başarısız oldu`
                : `Adım ${activeIndex + 1} / ${stages.length}: ${stages[activeIndex].label}`}
            </span>
            <span className="font-mono tabular-nums">{progressPct}%</span>
          </div>
          <progress
            role="progressbar"
            value={progressPct}
            max={100}
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={title}
            className="h-2.5 w-full overflow-hidden rounded-full accent-primary"
          />
        </div>

        <ol className="space-y-3">
          {stages.map((stage, idx) => {
            const done = failedStep === null && idx < activeIndex;
            const current = idx === activeIndex;
            return (
              <li
                key={stage.id}
                data-done={done ? "true" : undefined}
                className={cn(
                  "flex items-start gap-3 rounded-lg p-3 transition-colors",
                  current ? "bg-accent/60 text-foreground" : done ? "bg-muted/40 text-foreground" : "bg-muted/20 text-foreground",
                )}
              >
                <span className="stage-icon mt-0.5 shrink-0" aria-hidden="true">
                  {done ? (
                    <CheckCircle2 className="size-5 text-primary" />
                  ) : current ? (
                    <Loader2 className="size-5 animate-spin text-primary" />
                  ) : (
                    <Circle className="size-5 text-muted-foreground" />
                  )}
                </span>
                <div className="space-y-0.5">
                  <p className="text-sm font-medium">{stage.label}</p>
                  <p className="text-xs text-muted-foreground">{stage.detail}</p>
                </div>
              </li>
            );
          })}
        </ol>

        <div className="rounded-lg bg-muted/60 p-4">
          <p lang="tr" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Ön İzleme · Ayrıştırılan Yetkinlikler
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {previewTags.map((tag) => (
              <span
                key={tag}
                className="rounded-md bg-background px-2.5 py-1 text-xs font-medium text-foreground shadow-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 pt-2">
          {failedStep !== null && onRetryStep && (
            <Button type="button" size="lg" onClick={() => onRetryStep(failedStep)}>
              <RotateCcw className="size-4" />
              <span>{`${failedStep + 1}. Adımı Tekrar Dene`}</span>
            </Button>
          )}
          {onCancel && (
            <Button type="button" variant="outline" size="lg" onClick={onCancel}>
              <X className="size-4" />
              <span>İptal Et</span>
            </Button>
          )}
          {onBackground && (
            <Button type="button" variant="secondary" size="lg" onClick={onBackground}>
              <Bell className="size-4" />
              <span>Hazır Olunca Bildir</span>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
