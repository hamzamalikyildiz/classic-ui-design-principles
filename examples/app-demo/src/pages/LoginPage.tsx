import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getRequestedMockState } from "@/lib/api";
import { setSession } from "@/lib/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const mockState = getRequestedMockState();
  const [email, setEmail] = useState("cagla.inanc@kovan.io");
  const [password, setPassword] = useState("kovan-demo-2026");
  const [error, setError] = useState<string | null>(
    mockState === "error" ? "Oturum servisi şu an yanıt vermiyor." : null,
  );
  const [submitting, setSubmitting] = useState(mockState === "loading");

  function toggleTheme() {
    document.documentElement.classList.toggle("dark");
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("E-posta ve parola zorunludur.");
      return;
    }
    setError(null);
    setSubmitting(true);
    setSession(email.trim());
    navigate("/cv");
  }

  if (mockState === "long-loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Hazırlanıyor...</p>
        </div>
      </main>
    );
  }

  return (
    <main
      data-ready="true"
      className="flex min-h-screen flex-col items-center justify-center bg-background p-6"
    >
      <div className="w-full max-w-md space-y-6">
        <header className="rounded-xl bg-teal-700 p-6 text-white shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="size-6 shrink-0" />
              <div>
                <h1 className="text-xl font-bold tracking-tight text-balance">Kovan CV Platformu</h1>
                <p className="text-sm text-teal-100">Güvenli aday değerlendirme oturumu</p>
              </div>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              data-theme-toggle="true"
              onClick={toggleTheme}
            >
              Tema
            </Button>
          </div>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Oturum Aç</CardTitle>
            <CardDescription className="max-w-prose">
              Değerlendirme panosuna erişmek için kurumsal hesabınızla giriş yapın.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div
                role="alert"
                className="mb-4 rounded-lg bg-rose-100 px-4 py-3 text-sm text-rose-900 dark:bg-rose-950 dark:text-rose-200"
              >
                {error}
              </div>
            )}

            {mockState === "empty" ? (
              <div className="rounded-lg bg-muted p-6 text-center text-sm text-muted-foreground">
                Kayıtlı çalışma alanı bulunamadı. Demo hesabı ile oturum açabilirsiniz.
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium text-foreground">
                    E-posta
                  </label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="ad.soyad@kovan.io"
                    className="h-11"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-foreground">
                    Parola
                  </label>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="h-11"
                    required
                  />
                </div>

                <Button type="submit" size="lg" className="w-full" disabled={submitting}>
                  {submitting ? "Giriş yapılıyor..." : "Giriş Yap"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
