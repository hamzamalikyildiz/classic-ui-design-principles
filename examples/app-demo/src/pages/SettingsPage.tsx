import { useState, type FormEvent } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getRequestedMockState } from "@/lib/api";
import { getSession } from "@/lib/auth";

export function SettingsPage() {
  const mockState = getRequestedMockState();
  const user = getSession() ?? {
    email: "cagla.inanc@kovan.io",
    name: "Çağla İnanç",
    role: "Senior Product Designer",
  };
  const [name, setName] = useState(user.name);
  const [role, setRole] = useState(user.role);
  const [weeklyDigest, setWeeklyDigest] = useState(true);
  const [saved, setSaved] = useState(false);

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

  function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaved(true);
  }

  return (
    <div className="flex min-h-screen flex-col bg-background lg:flex-row">
      <Sidebar />
      <main data-ready="true" className="flex-1 space-y-6 p-6 lg:p-8">
        <section className="rounded-xl bg-teal-700 p-6 text-white shadow-sm">
          <h1 className="text-2xl font-bold tracking-tight text-balance">Hesap ve Tercihler</h1>
          <p className="mt-1 text-sm text-teal-100">
            Profil bilgilerinizi ve değerlendirme bildirimlerini yönetin.
          </p>
        </section>

        {mockState === "error" ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-destructive">
              Ayarlar yüklenirken beklenmeyen bir hata oluştu.
            </CardContent>
          </Card>
        ) : mockState === "empty" ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              Henüz yapılandırılmış tercih bulunmuyor.
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Profil Bilgileri</CardTitle>
              <CardDescription>
                Ekip değerlendirme notlarında görünecek ad ve rol bilginiz.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSave} className="max-w-lg space-y-4">
                <div className="space-y-2">
                  <label htmlFor="profile-name" className="text-sm font-medium">
                    Ad Soyad
                  </label>
                  <Input
                    id="profile-name"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      setSaved(false);
                    }}
                    className="h-11"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="profile-role" className="text-sm font-medium">
                    Ünvan
                  </label>
                  <Input
                    id="profile-role"
                    value={role}
                    onChange={(e) => {
                      setRole(e.target.value);
                      setSaved(false);
                    }}
                    className="h-11"
                  />
                </div>

                <label className="flex items-center gap-3 rounded-lg bg-muted/60 p-4 text-sm">
                  <input
                    type="checkbox"
                    checked={weeklyDigest}
                    onChange={(e) => {
                      setWeeklyDigest(e.target.checked);
                      setSaved(false);
                    }}
                    className="size-4 accent-primary"
                  />
                  <span>Haftalık AI skor özeti e-postası gönder</span>
                </label>

                <div className="flex items-center gap-4 pt-2">
                  <Button type="submit" size="lg">
                    Tercihleri Kaydet
                  </Button>
                  {saved && (
                    <span className="text-sm font-medium text-primary">
                      Tercihler kaydedildi.
                    </span>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
