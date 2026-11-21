import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Lock,
  Plus,
  RefreshCw,
  Sparkles,
  WifiOff,
} from "lucide-react";
import { FilterChip } from "@/components/FilterChip";
import { LongOperationPanel } from "@/components/LongOperationPanel";
import { Sidebar } from "@/components/Sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchApplications, getRequestedMockState } from "@/lib/api";
import type { Application, ApplicationStatus } from "@/types/cv";

const STATUS_FILTERS: Array<{ key: "all" | ApplicationStatus; label: string }> = [
  { key: "all", label: "Tümü" },
  { key: "accepted", label: "Kabul Edildi" },
  { key: "in_review", label: "İncelemede" },
  { key: "draft", label: "Taslak" },
  { key: "failed", label: "Hata" },
];

function statusBadgeVariant(status: ApplicationStatus) {
  switch (status) {
    case "accepted":
      return "success" as const;
    case "in_review":
      return "warning" as const;
    case "failed":
      return "destructive" as const;
    default:
      return "secondary" as const;
  }
}

function statusText(status: ApplicationStatus) {
  switch (status) {
    case "accepted":
      return "Kabul Edildi";
    case "in_review":
      return "İncelemede";
    case "draft":
      return "Taslak";
    case "failed":
      return "Başarısız";
  }
}

const salaryFormatter = new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
});

const relativeFormatter = new Intl.RelativeTimeFormat("tr-TR", { numeric: "auto" });

export function CvListPage() {
  const mockState = getRequestedMockState();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [revalidating, setRevalidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<"all" | ApplicationStatus>("all");
  const [longWaitDismissed, setLongWaitDismissed] = useState(false);
  const [isOffline, setIsOffline] = useState(
    () => (typeof navigator !== "undefined" ? !navigator.onLine : false) || mockState === "offline",
  );
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
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
      const items = await fetchApplications();
      setApplications(items);
      if (background) {
        setStatusMessage("Başvuru listesi güncellendi.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Başvurular yüklenemedi");
    } finally {
      setLoading(false);
      setRevalidating(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function handleAddSampleCv() {
    if (isOffline || isLocked) return;
    const nextItem: Application = {
      id: `app_new_${Date.now()}`,
      candidate: "Zeynep Karahan",
      role: "Staff Frontend Engineer",
      company: "Kovan Teknoloji",
      score: 84,
      salary: 145000,
      status: "in_review",
      updatedLabel: "Az önce",
      updatedAt: new Date().toISOString(),
      skills: ["React 19", "TypeScript", "Design Systems"],
      scoreHistory: [{ id: "rev1", label: "İlk", score: 84 }],
      scoreBreakdown: [
        { label: "Teknik Uyum", value: 88 },
        { label: "Etki Metrikleri", value: 80 },
      ],
      recommendations: [],
      interviewQuestions: [],
    };
    setApplications((prev) => [nextItem, ...prev]);
    setStatusMessage("Zeynep Karahan başvurusu listeye eklendi.");
  }

  if (loading && mockState === "long-loading" && !longWaitDismissed) {
    return (
      <div className="flex min-h-screen flex-col bg-background lg:flex-row">
        <Sidebar />
        <main className="flex flex-1 items-center justify-center p-6">
          <LongOperationPanel
            title="Başvuru Havuzu Eşleştiriliyor"
            subtitle="Tüm aday CV'leri güncel rol kriterleriyle yeniden puanlanıyor."
            onCancel={() => {
              setLongWaitDismissed(true);
              setLoading(false);
            }}
            onBackground={() => {
              setLongWaitDismissed(true);
              setStatusMessage("Eşleştirme arka planda sürüyor; tamamlandığında bildirilecek.");
            }}
          />
        </main>
      </div>
    );
  }

  const filtered =
    selectedStatus === "all"
      ? applications
      : applications.filter((app) => app.status === selectedStatus);

  const hasPartialRows = applications.some((app) => app.salary === null);

  return (
    <div className="flex min-h-screen flex-col bg-background lg:flex-row">
      <Sidebar />
      <main
        data-ready={!loading ? "true" : undefined}
        aria-busy={loading || revalidating ? "true" : "false"}
        className="flex-1 space-y-6 p-6 lg:p-8"
      >
        <section className="rounded-xl bg-teal-700 p-6 text-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm text-teal-100">
                <Sparkles className="size-4" aria-hidden="true" />
                <span>2026 Q4 Yetenek Havuzu</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-balance">
                Aday Başvuru Listesi
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <div className="rounded-lg bg-teal-800/80 px-4 py-2 text-right">
                <p className="text-xs text-teal-100">Toplam Başvuru</p>
                <p className="font-mono text-2xl font-bold tabular-nums">{applications.length}</p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="lg"
                disabled={isOffline || isLocked}
                onClick={handleAddSampleCv}
              >
                <Plus className="size-4" aria-hidden="true" />
                <span>CV Yükle</span>
              </Button>
            </div>
          </div>
        </section>

        {isOffline && (
          <div
            role="status"
            aria-live="polite"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-amber-100 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200"
          >
            <div className="flex items-center gap-2">
              <WifiOff className="size-4 shrink-0" aria-hidden="true" />
              <span>
                Çevrimdışı — {relativeFormatter.format(-2, "minute")} önbelleğe alınan veri
                okunuyor. Ağ işlemleri duraklatıldı.
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
              <span id="locked-list-desc">
                Yeni CV yükleme ve toplu dışa aktarma için Yönetici yetkisi gerekir.
              </span>
            </div>
            <Button type="button" variant="outline" size="sm">
              Yetki Talep Et
            </Button>
          </div>
        )}

        {statusMessage && (
          <div
            role="status"
            aria-live="polite"
            className="rounded-lg bg-emerald-100 px-4 py-2.5 text-sm font-medium text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
          >
            {statusMessage}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-muted/70 p-2">
          {STATUS_FILTERS.map((item) => (
            <FilterChip
              key={item.key}
              label={item.label}
              selected={selectedStatus === item.key}
              onClick={() => setSelectedStatus(item.key)}
            />
          ))}
        </div>

        {loading ? (
          <div className="space-y-4" aria-hidden="true">
            {[1, 2, 3].map((row) => (
              <div key={row} className="h-24 animate-pulse rounded-xl bg-muted p-6" />
            ))}
          </div>
        ) : error ? (
          <Card role="alert">
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="size-8 text-destructive" aria-hidden="true" />
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground text-balance">
                  Başvurular yüklenemedi
                </h2>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">{error}</p>
              </div>
              <Button type="button" size="lg" onClick={() => void load()}>
                <RefreshCw className="size-4" aria-hidden="true" />
                <span>Tekrar Dene</span>
              </Button>
            </CardContent>
          </Card>
        ) : applications.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <svg
                width="64"
                height="64"
                viewBox="0 0 64 64"
                fill="none"
                aria-hidden="true"
                className="text-primary"
              >
                <rect x="12" y="8" width="40" height="48" rx="6" stroke="currentColor" strokeWidth="2.5" />
                <path d="M22 22h20M22 32h20M22 42h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground text-balance">
                  Rol uyumunu puanlamak için ilk CV&apos;yi yükleyin
                </h2>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">
                  Henüz kayıtlı başvuru bulunmuyor. Aday özgeçmişi ekleyerek AI uyum skorunu görebilirsiniz.
                </p>
              </div>
              <Button type="button" size="lg" disabled={isOffline || isLocked} onClick={handleAddSampleCv}>
                <Plus className="size-4" aria-hidden="true" />
                <span>CV Yükle</span>
              </Button>
            </CardContent>
          </Card>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="space-y-1" aria-live="polite">
                <h2 className="text-lg font-semibold text-foreground text-balance">
                  Seçili filtre için 0 sonuç
                </h2>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">
                  &ldquo;{STATUS_FILTERS.find((f) => f.key === selectedStatus)?.label}&rdquo; durumunda
                  aday bulunamadı.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setSelectedStatus("all")}
              >
                Filtreleri Temizle
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <CardTitle>Kayıtlı Başvurular</CardTitle>
                  <CardDescription>
                    Skor, maaş beklentisi ve son güncellemeye göre sıralanır.
                  </CardDescription>
                </div>
                {hasPartialRows && (
                  <Button type="button" variant="outline" size="sm" onClick={() => void load(true)}>
                    Eksik Veriyi Yenile
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/70 text-xs font-medium text-muted-foreground">
                    <th scope="col" className="pb-3 pr-4">Aday</th>
                    <th scope="col" className="pb-3 pr-4">Pozisyon &amp; Şirket</th>
                    <th scope="col" className="pb-3 pr-4 text-right">Skor</th>
                    <th scope="col" className="pb-3 pr-4 text-right">Maaş Beklentisi</th>
                    <th scope="col" className="pb-3 pr-4">Durum</th>
                    <th scope="col" className="pb-3 pr-4">Güncellendi</th>
                    <th scope="col" className="pb-3 text-right">Detay</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((app) => (
                    <tr
                      key={app.id}
                      className="h-12 border-b border-border/50 transition-colors hover:bg-muted/50"
                    >
                      <td className="py-3 pr-4 font-medium text-foreground">
                        {app.candidate}
                      </td>
                      <td className="max-w-xs py-3 pr-4">
                        <p className="truncate font-medium text-foreground">{app.role}</p>
                        <p className="text-xs text-muted-foreground">{app.company}</p>
                      </td>
                      <td className="py-3 pr-4 text-right font-mono font-semibold tabular-nums">
                        {app.score}
                      </td>
                      <td className="py-3 pr-4 text-right font-mono tabular-nums">
                        {app.salary !== null ? (
                          salaryFormatter.format(app.salary)
                        ) : (
                          <span aria-label="Metric pending" className="text-muted-foreground">
                            —
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={statusBadgeVariant(app.status)}>
                          {statusText(app.status)}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">{app.updatedLabel}</td>
                      <td className="py-3 text-right">
                        <Link
                          to={`/cv/${app.id}`}
                          className="inline-flex h-9 items-center gap-1 rounded-md px-3 text-sm font-medium text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        >
                          <span>İncele</span>
                          <ArrowRight className="size-4" aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
