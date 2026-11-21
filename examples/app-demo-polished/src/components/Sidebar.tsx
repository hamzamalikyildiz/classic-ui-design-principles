import { Link, useLocation, useNavigate } from "react-router-dom";
import { FileText, LogOut, Settings, Users } from "lucide-react";
import { clearSession } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

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
        <div className="space-y-3">
          <div>
            <p className="text-base font-bold tracking-tight text-foreground">Kovan CV</p>
            <p className="text-xs text-muted-foreground">Aday Değerlendirme</p>
          </div>
          <ThemeToggle />
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
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
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
          <LogOut className="size-4" aria-hidden="true" />
          <span>Çıkış Yap</span>
        </Button>
      </div>
    </aside>
  );
}
