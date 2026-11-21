import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { FilterChip } from "@/components/FilterChip";
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

export function CvListPage() {
  const mockState = getRequestedMockState();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<"all" | ApplicationStatus>("all");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchApplications();
      setApplications(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Başvurular yüklenemedi");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading && mockState === "long-loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Hazırlanıyor...</p>
        </div>
      </main>
    );
  }

  const filtered =
    selectedStatus === "all"
      ? applications
      : applications.filter((app) => app.status === selectedStatus);

  return (
    <div className="flex min-h-screen flex-col bg-background lg:flex-row">
      <Sidebar />
      <main
        data-ready={!loading ? "true" : undefined}
        className="flex-1 space-y-6 p-6 lg:p-8"
      >
        <section className="rounded-xl bg-teal-700 p-6 text-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm text-teal-100">
                <Sparkles className="size-4" />
                <span>2026 Q4 Yetenek Havuzu</span>
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-balance">
                Aday Başvuru Listesi
              </h1>
            </div>
            <div className="rounded-lg bg-teal-800/80 px-4 py-2 text-right">
              <p className="text-xs text-teal-100">Toplam Başvuru</p>
              <p className="font-mono text-2xl font-bold tabular-nums">{applications.length}</p>
            </div>
          </div>
        </section>

        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-slate-50 p-2">
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
          <div className="space-y-4">
            {[1, 2, 3].map((row) => (
              <div
                key={row}
                className="h-24 animate-pulse rounded-xl bg-muted p-6"
                aria-hidden="true"
              />
            ))}
          </div>
        ) : error ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="size-8 text-destructive" />
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground text-balance">
                  Başvurular yüklenemedi
                </h2>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">{error}</p>
              </div>
              <Button type="button" size="lg" onClick={() => void load()}>
                <RefreshCw className="size-4" />
                <span>Tekrar Dene</span>
              </Button>
            </CardContent>
          </Card>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-10 text-center">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold text-foreground text-balance">
                  Gösterilecek başvuru yok
                </h2>
                <p className="max-w-prose text-sm text-muted-foreground text-pretty">
                  Seçili filtreye uygun aday bulunamadı veya liste henüz boş.
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
              <CardTitle>Kayıtlı Başvurular</CardTitle>
              <CardDescription>
                Skor, maaş beklentisi ve son güncellemeye göre sıralanır.
              </CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border/70 text-xs font-medium text-muted-foreground">
                    <th className="pb-3 pr-4">Aday</th>
                    <th className="pb-3 pr-4">Pozisyon & Şirket</th>
                    <th className="pb-3 pr-4 text-right">Skor</th>
                    <th className="pb-3 pr-4 text-right">Maaş Beklentisi</th>
                    <th className="pb-3 pr-4">Durum</th>
                    <th className="pb-3 pr-4">Güncellendi</th>
                    <th className="pb-3 text-right">Detay</th>
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
                          <ArrowRight className="size-4" />
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
