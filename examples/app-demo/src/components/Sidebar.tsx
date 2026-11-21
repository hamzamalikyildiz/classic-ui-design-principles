import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { FileText, LogOut, Moon, Settings, Sun, Users } from "lucide-react";
import { clearSession } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// FALSE-POSITIVE TRAP #4: component file with no hero surface -> INFO in file mode, not WARN
export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const [dark, setDark] = useState(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("dark"),
  );

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
  }

  function handleLogout() {
    clearSession();
    navigate("/login");
  }

  const links = [
    { to: "/cv", label: "Başvurular", icon: Users },
    { to: "/cv/app_01", label: "Örnek CV", icon: FileText },
    { to: "/settings", label: "Ayarlar", icon: Settings },
  ];

  return (
    <aside className="flex w-full shrink-0 flex-col justify-between gap-6 border-b border-border/70 bg-card p-5 lg:w-64 lg:border-r lg:border-b-0">
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-base font-bold tracking-tight text-foreground">Kovan CV</p>
            <p className="text-xs text-muted-foreground">Aday Değerlendirme</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="icon"
            data-theme-toggle="true"
            aria-label={dark ? "Aydınlık temaya geç" : "Karanlık temaya geç"}
            onClick={toggleTheme}
          >
            {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </Button>
        </div>

        <nav aria-label="Ana menü" className="flex flex-row gap-2 overflow-x-auto lg:flex-col">
          {links.map((item) => {
            const Icon = item.icon;
            const active =
              item.to === "/cv"
                ? location.pathname === "/cv"
                : location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="hidden border-t border-border/60 pt-4 lg:block">
        <Button
          type="button"
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-foreground"
          onClick={handleLogout}
        >
          <LogOut className="size-4" />
          <span>Çıkış Yap</span>
        </Button>
      </div>
    </aside>
  );
}
