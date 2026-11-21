import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Lock,
  RefreshCw,
  RotateCcw,
  Sparkles,
  WifiOff,
  XCircle,
} from "lucide-react";
import { ActionBar } from "@/components/ActionBar";
import { FilterChip } from "@/components/FilterChip";
import { LongOperationPanel } from "@/components/LongOperationPanel";
import { ScoreCard } from "@/components/ScoreCard";
import { Sidebar } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { analyzeApplication, fetchApplicationById, getRequestedMockState } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Application, RecommendationStatus } from "@/types/cv";

const REC_FILTERS: Array<{ key: "all" | RecommendationStatus; label: string }> = [
  { key: "all", label: "Tümü" },
  { key: "pending", label: "Bekleyen" },
  { key: "accepted", label: "Kabul Edilen" },
  { key: "dismissed", label: "Reddedilen" },
];

function recStatusLabel(status: RecommendationStatus) {
  switch (status) {
    case "accepted":
      return "Kabul Edildi";
    case "dismissed":
      return "Reddedildi";
    case "pending":
      return "Bekliyor";
  }
}

const relativeFormatter = new Intl.RelativeTimeFormat("tr-TR", { numeric: "auto" });

export function CvDetailPage() {
  const { id = "app_01" } = useParams();
  const mockState = getRequestedMockState();
  const [application, setApplication] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [revalidating, setRevalidating] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [longWaitDismissed, setLongWaitDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recFilter, setRecFilter] = useState<"all" | RecommendationStatus>("all");
  const [isEditing, setIsEditing] = useState(false);
  const [note, setNote] = useState("Design systems & OKLCH token geçişi güçlü.");
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [acceptedFlashId, setAcceptedFlashId] = useState<string | null>(null);
  const [undoToast, setUndoToast] = useState<{
    recId: string;
    prevStatus: RecommendationStatus;
    title: string;
  } | null>(null);
  const [isOffline, setIsOffline] = useState(
    () => (typeof navigator !== "undefined" ? !navigator.onLine : false) || mockState === "offline",
  );
  const undoTimerRef = useRef<number | null>(null);
  const isLocked = mockState === "locked";
  const isStale = mockState === "stale";

  useEffect(() => {
    const onOnline = () => setIsOffline(false);
    const onOffline = () => setIsOffline(true);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  async function load(background = false) {
    if (background) {
      setRevalidating(true);
    } else {
      setLoading(true);
    }
    setError(null);
    try {
      const item = await fetchApplicationById(id);
      setApplication(item);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Detay yüklenemedi");
    } finally {
      setLoading(false);
      setRevalidating(false);
    }
  }

  useEffect(() => {
    void load();
  }, [id]);

  async function handleRunAnalysis() {
    if (isOffline || isLocked) return;
    setAnalyzing(true);
    try {
      await new Promise((r) => setTimeout(r, 4500));
      const updated = await analyzeApplication(id);
      setApplication(updated);
      setExportMsg("AI uyumluluk analizi tamamlandı ve skor güncellendi.");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleExport() {
    setExportMsg("Rapor PDF olarak dışa aktarıldı.");
  }

  function updateRecommendation(recId: string, nextStatus: RecommendationStatus) {
    const current = application?.recommendations.find((r) => r.id === recId);
    const prevStatus = current?.status ?? "pending";
    const title = current?.title ?? "Öneri";

    setApplication((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        recommendations: prev.recommendations.map((rec) =>
          rec.id === recId ? { ...rec, status: nextStatus } : rec,
        ),
      };
    });

    if (nextStatus === "accepted") {
      setAcceptedFlashId(recId);
      window.setTimeout(() => setAcceptedFlashId((cur) => (cur === recId ? null : cur)), 1200);
    }

    if (undoTimerRef.current) {
      window.clearTimeout(undoTimerRef.current);
    }
    setUndoToast({ recId, prevStatus, title });
    undoTimerRef.current = window.setTimeout(() => setUndoToast(null), 4000);
  }

  function handleUndoRecommendation() {
    if (!undoToast) return;
    const { recId, prevStatus } = undoToast;
    setApplication((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        recommendations: prev.recommendations.map((rec) =>
          rec.id === recId ? { ...rec, status: prevStatus } : rec,
        ),
      };
    });
    setUndoToast(null);
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

  if ((loading && mockState === "long-loading" && !longWaitDismissed) || analyzing) {
    return (
      <div className="flex min-h-screen flex-col bg-background lg:flex-row">
        <Sidebar />
        <main className="flex flex-1 items-center justify-center p-6">
          <LongOperationPanel
            previewTags={application?.skills ?? ["Design Systems", "OKLCH", "React 19", "A11y"]}
            onCancel={() => {
              setAnalyzing(false);
              setLongWaitDismissed(true);
              setLoading(false);
            }}
            onBackground={() => {
              setAnalyzing(false);
              setLongWaitDismissed(true);
              setExportMsg("Analiz arka planda sürüyor; tamamlandığında bildirilecek.");
            }}
          />
        </main>
      </div>
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
        aria-busy={loading || revalidating ? "true" : "false"}
        className="flex-1 space-y-6 p-6 lg:p-8"
      >
        <div className="flex items-center justify-between gap-4">
          <Link
            to="/cv"
            className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            <span>Başvurulara Dön</span>
          </Link>

          <span className="inline-block rounded-md bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
            Arşiv Notu
          </span>
        </div>

        {isOffline && (
          <div
            role="status"
            aria-live="polite"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-amber-100 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200"
          >
            <div className="flex items-center gap-2">
              <WifiOff className="size-4 shrink-0" aria-hidden="true" />
              <span>
                Çevrimdışı — önbellekteki aday verisi gösteriliyor. Değerlendirme notunuz yerel
                olarak korunur.
              </span>
            </div>
            <Button type="button" variant="outline" size="sm" onClick={() => void load(true)}>
              Tekrar Dene
            </Button>
          </div>
        )}

        {isStale && !isOffline && (
          <div
            role="status"
            aria-live="polite"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted px-4 py-2.5 text-sm text-muted-foreground"
          >
            <span>
              {revalidating
                ? "Arka planda güncelleniyor..."
                : `Son güncelleme: ${relativeFormatter.format(-4, "minute")}`}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={revalidating}
              onClick={() => void load(true)}
            >
              <RefreshCw className="size-4" aria-hidden="true" />
              <span>Yenile</span>
            </Button>
          </div>
        )}

        {isLocked && (
          <div
            role="status"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted px-4 py-3 text-sm text-foreground"
          >
            <div className="flex items-center gap-2">
              <Lock className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <span id="locked-detail-desc">
                AI analizi başlatma ve öneri onaylama için Yönetici veya Pro yetkisi gerekir.
              </span>
            </div>
            <Button type="button" variant="outline" size="sm">
              Yetki Talep Et
            </Button>
          </div>
        )}

        {loading ? (
          <div className="space-y-4" aria-hidden="true">
            <div className="h-32 animate-pulse rounded-xl bg-muted" />
            <div className="h-48 animate-pulse rounded-xl bg-muted" />
          </div>
        ) : error ? (
          <Card role="alert">
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
              <div className="space-y-1">
                <h1 className="text-lg font-semibold text-foreground text-balance">
                  Başvuru detayı yüklenemedi
                </h1>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">{error}</p>
              </div>
              <Button type="button" size="lg" onClick={() => void load()}>
                <RefreshCw className="size-4" aria-hidden="true" />
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
                    <Badge variant="secondary">AI Önizleme Modu</Badge>
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

                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    size="lg"
                    disabled={isOffline || isLocked}
                    aria-describedby={isLocked ? "locked-detail-desc" : undefined}
                    onClick={() => void handleRunAnalysis()}
                  >
                    <Sparkles className="size-4" aria-hidden="true" />
                    <span>30s AI Analizi Başlat</span>
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    className="border-white/40 bg-transparent text-white hover:bg-white/15 hover:text-white"
                    onClick={handleExport}
                  >
                    Raporu Dışa Aktar
                  </Button>
                </div>
              </div>
              {exportMsg && (
                <p role="status" aria-live="polite" className="mt-3 text-xs text-teal-100">
                  {exportMsg}
                </p>
              )}
            </section>

            <ScoreCard
              score={application.score}
              history={application.scoreHistory}
              breakdown={application.scoreBreakdown}
            />

            <Card>
              <CardHeader>
                <h2 lang="tr" className="text-sm font-semibold uppercase tracking-wider text-muted-foreground text-balance">
                  İnceleme Özeti
                </h2>
                <CardTitle>AI İyileştirme Önerileri</CardTitle>
                <CardDescription>
                  Skoru artırmak için önerileri kabul edebilir veya reddedebilirsiniz.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2 rounded-lg bg-muted/70 p-2">
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
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted p-4 text-sm text-muted-foreground">
                    <span>Bu filtrede öneri bulunmuyor.</span>
                    <Button type="button" variant="outline" size="sm" onClick={() => setRecFilter("all")}>
                      Filtreyi Temizle
                    </Button>
                  </div>
                ) : (
                  <ul className="space-y-3">
                    {visibleRecs.map((rec) => (
                      <li
                        key={rec.id}
                        className={cn(
                          "flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted/60 p-4",
                          acceptedFlashId === rec.id && "row-ok",
                        )}
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
                            {recStatusLabel(rec.status)}
                          </Badge>
                          {rec.status === "pending" && (
                            <>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                disabled={isLocked}
                                onClick={() => updateRecommendation(rec.id, "accepted")}
                              >
                                <CheckCircle2 className="size-4" aria-hidden="true" />
                                <span>Kabul Et</span>
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                disabled={isLocked}
                                onClick={() => updateRecommendation(rec.id, "dismissed")}
                              >
                                <XCircle className="size-4" aria-hidden="true" />
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
                          disabled={isLocked}
                          onClick={() => recordAnswer(q.id)}
                        >
                          Yanıt Kaydet
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

            <ActionBar
              isEditing={isEditing}
              onEdit={() => setIsEditing(true)}
              onSave={() => setIsEditing(false)}
            />
          </>
        )}

        {undoToast && (
          <div
            role="status"
            aria-live="polite"
            className="toast-motion fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-4 rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-lg"
          >
            <span>Öneri güncellendi: {undoToast.title}</span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleUndoRecommendation}
            >
              <RotateCcw className="size-3.5" aria-hidden="true" />
              <span>Geri Al</span>
            </Button>
          </div>
        )}
      </main>
    </div>
  );
}
