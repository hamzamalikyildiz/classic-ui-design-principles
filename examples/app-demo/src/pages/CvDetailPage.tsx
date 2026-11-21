import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, CheckCircle2, RefreshCw, Sparkles, XCircle } from "lucide-react";
import { ActionBar } from "@/components/ActionBar";
import { FilterChip } from "@/components/FilterChip";
import { ScoreCard } from "@/components/ScoreCard";
import { Sidebar } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeApplication, fetchApplicationById, getRequestedMockState } from "@/lib/api";
import type { Application, RecommendationStatus } from "@/types/cv";

const REC_FILTERS: Array<{ key: "all" | RecommendationStatus; label: string }> = [
  { key: "all", label: "Tümü" },
  { key: "pending", label: "Bekleyen" },
  { key: "accepted", label: "Kabul Edilen" },
  { key: "dismissed", label: "Reddedilen" },
];

export function CvDetailPage() {
  const { id = "app_01" } = useParams();
  const mockState = getRequestedMockState();
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recFilter, setRecFilter] = useState<"all" | RecommendationStatus>("all");
  const [isEditing, setIsEditing] = useState(false);
  const [note, setNote] = useState("Design systems & OKLCH token geçişi güçlü.");
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const item = await fetchApplicationById(id);
      setApplication(item);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Detay yüklenemedi");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [id]);

  async function handleRunAnalysis() {
    setAnalyzing(true);
    try {
      await new Promise((r) => setTimeout(r, 4500));
      const updated = await analyzeApplication(id);
      setApplication(updated);
    } finally {
      setAnalyzing(false);
    }
  }

  function handleExport() {
    setExportMsg("Rapor PDF olarak dışa aktarıldı.");
  }

  function updateRecommendation(recId: string, nextStatus: RecommendationStatus) {
    setApplication((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        recommendations: prev.recommendations.map((rec) =>
          rec.id === recId ? { ...rec, status: nextStatus } : rec,
        ),
      };
    });
  }

  function recordAnswer(qId: string) {
    setApplication((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        interviewQuestions: prev.interviewQuestions.map((q) =>
          q.id === qId
            ? {
                ...q,
                answer: "Tasarımdan üretime bileşen kullanım oranı haftalık telemetri ile ölçülüyor.",
                score: "4.2/5",
                status: "answered",
              }
            : q,
        ),
      };
    });
  }

  // DELIBERATE DEFECT #5: bare spinner + "Hazırlanıyor..." without steps/progress/cancel (WARN long-wait-unexplained)
  if ((loading && mockState === "long-loading") || analyzing) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Hazırlanıyor...</p>
        </div>
      </main>
    );
  }

  const visibleRecs = application
    ? recFilter === "all"
      ? application.recommendations
      : application.recommendations.filter((r) => r.status === recFilter)
    : [];

  return (
    <div className="flex min-h-screen flex-col bg-background lg:flex-row">
      <Sidebar />
      <main
        data-ready={!loading ? "true" : undefined}
        className="flex-1 space-y-6 p-6 lg:p-8"
      >
        <div className="flex items-center justify-between gap-4">
          <Link
            to="/cv"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft className="size-4" />
            <span>Başvurulara Dön</span>
          </Link>

          {/* DELIBERATE DEFECT #1: same-branch low contrast (bg-slate-100 text-slate-300 -> FAIL wcag-aa) */}
          <span className="inline-block rounded-md bg-slate-100 px-3 py-1 text-xs text-slate-300">
            Arşiv Notu
          </span>
        </div>

        {loading ? (
          <div className="space-y-4">
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
            <div className="h-48 animate-pulse rounded-xl bg-muted" />
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="size-8 text-destructive" />
              <div className="space-y-1">
                <h1 className="text-lg font-semibold text-foreground text-balance">
                  Başvuru detayı yüklenemedi
                </h1>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">{error}</p>
              </div>
              <Button type="button" size="lg" onClick={() => void load()}>
                <RefreshCw className="size-4" />
                <span>Tekrar Dene</span>
              </Button>
            </CardContent>
          </Card>
        ) : !application ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <h1 className="text-lg font-semibold text-foreground text-balance">
                Başvuru kaydı boş
              </h1>
              <p className="max-w-prose text-sm text-muted-foreground text-pretty">
                Seçili aday için henüz veri bulunmuyor.
              </p>
              <Link
                to="/cv"
                className="inline-flex h-11 items-center rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground"
              >
                Listeye Dön
              </Link>
            </CardContent>
          </Card>
        ) : (
          <>
            <section className="rounded-xl bg-teal-700 p-6 text-white shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-2xl font-bold tracking-tight text-balance">
                      {application.candidate}
                    </h1>
                    {/* DELIBERATE DEFECT #3: 10px micro-badge (shadcn-defaults / tiny text) */}
                    <Badge variant="micro" className="text-[10px]">
                      AI Önizleme Modu
                    </Badge>
                  </div>
                  <p className="text-sm text-teal-100">
                    {application.role} · {application.company}
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {application.skills.map((skill) => (
                      <span
                        key={skill}
                        className="rounded-md bg-teal-800/80 px-2.5 py-1 text-xs font-medium text-teal-50"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                {/* DELIBERATE DEFECT #2: 2 simultaneously visible solid primary buttons in one block (WARN single-primary-cta) */}
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" size="lg" onClick={() => void handleRunAnalysis()}>
                    <Sparkles className="size-4" />
                    <span>30s AI Analizi Başlat</span>
                  </Button>
                  <Button type="button" size="lg" onClick={handleExport}>
                    Raporu Dışa Aktar
                  </Button>
                </div>
              </div>
              {exportMsg && (
                <p className="mt-3 text-xs text-teal-100">{exportMsg}</p>
              )}
            </section>

            {/* FALSE-POSITIVE TRAP #1: ScoreCard (bg-slate-900) imports ScoreBars (text-white/80) */}
            <ScoreCard
              score={application.score}
              history={application.scoreHistory}
              breakdown={application.scoreBreakdown}
            />

            <Card>
              <CardHeader>
                {/* DELIBERATE DEFECT #4: uppercase Turkish text without Turkish lang attr (WARN tr-uppercase + tr-uppercase-render) */}
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground text-balance">
                  İnceleme Özeti
                </h2>
                <CardTitle>AI İyileştirme Önerileri</CardTitle>
                <CardDescription>
                  Skoru artırmak için önerileri kabul edebilir veya reddedebilirsiniz.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2 rounded-lg bg-slate-50 p-2">
                  {REC_FILTERS.map((f) => (
                    <FilterChip
                      key={f.key}
                      label={f.label}
                      selected={recFilter === f.key}
                      onClick={() => setRecFilter(f.key)}
                    />
                  ))}
                </div>

                {visibleRecs.length === 0 ? (
                  <p className="rounded-lg bg-muted p-4 text-sm text-muted-foreground">
                    Bu filtrede öneri bulunmuyor.
                  </p>
                ) : (
                  <ul className="space-y-3">
                    {visibleRecs.map((rec) => (
                      <li
                        key={rec.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted/60 p-4"
                      >
                        <div className="flex items-center gap-3">
                          <span className="rounded-md bg-accent px-2.5 py-1 font-mono text-xs font-semibold text-accent-foreground tabular-nums">
                            {rec.delta}
                          </span>
                          <span className="text-sm font-medium text-foreground">
                            {rec.title}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              rec.status === "accepted"
                                ? "success"
                                : rec.status === "dismissed"
                                  ? "outline"
                                  : "warning"
                            }
                          >
                            {rec.status}
                          </Badge>
                          {rec.status === "pending" && (
                            <>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => updateRecommendation(rec.id, "accepted")}
                              >
                                <CheckCircle2 className="size-4" />
                                <span>Kabul Et</span>
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => updateRecommendation(rec.id, "dismissed")}
                              >
                                <XCircle className="size-4" />
                                <span>Reddet</span>
                              </Button>
                            </>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Mülakat Soruları</CardTitle>
                <CardDescription>
                  Yanıtlanmamış sorular kısmi veri durumunda listelenir.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {application.interviewQuestions.map((q) => (
                  <div
                    key={q.id}
                    className="flex flex-col justify-between gap-3 rounded-lg bg-muted/60 p-4 sm:flex-row sm:items-center"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-foreground">{q.question}</p>
                      <p className="max-w-prose text-sm text-muted-foreground text-pretty">
                        {q.answer ?? "Henüz yanıt kaydedilmedi."}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="font-mono text-sm font-semibold tabular-nums text-foreground">
                        {q.score ?? (
                          <span aria-label="Metric pending" className="text-muted-foreground">
                            —
                          </span>
                        )}
                      </span>
                      {q.status === "partial" && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => recordAnswer(q.id)}
                        >
                          Record answer
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {isEditing && (
              <Card>
                <CardContent>
                  <label htmlFor="reviewer-note" className="mb-2 block text-sm font-medium">
                    Değerlendirme Notu
                  </label>
                  <textarea
                    id="reviewer-note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    rows={3}
                    className="w-full rounded-md border border-input bg-background p-3 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </CardContent>
              </Card>
            )}

            {/* FALSE-POSITIVE TRAP #3: mutually exclusive solid primary CTAs */}
            <ActionBar
              isEditing={isEditing}
              onEdit={() => setIsEditing(true)}
              onSave={() => setIsEditing(false)}
            />
          </>
        )}
      </main>
    </div>
  );
}
