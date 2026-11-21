import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

export type ThemeMode = "system" | "light" | "dark";

function applyTheme(mode: ThemeMode) {
  const prefersDark =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = mode === "dark" || (mode === "system" && prefersDark);
  document.documentElement.classList.toggle("dark", isDark);
}

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const stored = localStorage.getItem("theme");
    return stored === "light" || stored === "dark" || stored === "system" ? stored : "system";
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem("theme", theme);
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => applyTheme("system");
    mq.addEventListener("change", listener);
    return () => mq.removeEventListener("change", listener);
  }, [theme]);

  const options: Array<{ key: ThemeMode; label: string; icon: typeof Monitor }> = [
    { key: "system", label: "Sistem", icon: Monitor },
    { key: "light", label: "Aydınlık", icon: Sun },
    { key: "dark", label: "Karanlık", icon: Moon },
  ];

  return (
    <div
      role="group"
      aria-label="Tema"
      data-theme-toggle="true"
      className={cn("inline-flex rounded-lg bg-muted p-1", className)}
    >
      {options.map((opt) => {
        const Icon = opt.icon;
        const active = theme === opt.key;
        return (
          <button
            key={opt.key}
            type="button"
            aria-pressed={active}
            onClick={() => setTheme(opt.key)}
            className={cn(
              "inline-flex h-8 items-center gap-1 rounded px-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5 shrink-0" aria-hidden="true" />
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
