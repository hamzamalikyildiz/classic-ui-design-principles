import seed from "../../seed.json";
import type { Application, SeedPayload } from "@/types/cv";

declare global {
  interface Window {
    __RENDER_STATE__?: string;
    __UI_STATE__?: string;
  }
}

export function getRequestedMockState(): string | null {
  const params = new URLSearchParams(window.location.search);
  const queryState = params.get("state");
  if (queryState) return queryState;
  if (window.__RENDER_STATE__ && window.__RENDER_STATE__ !== "default") {
    return window.__RENDER_STATE__;
  }
  return null;
}

function getSeedApplications(): Application[] {
  return (seed as SeedPayload).applications.map((item) => ({ ...item }));
}

async function fallbackMockFetch(url: string, init?: RequestInit): Promise<Response> {
  const parsed = new URL(url, window.location.origin);
  const state = parsed.searchParams.get("state") ?? getRequestedMockState();

  if (state === "loading") {
    await new Promise((r) => setTimeout(r, 2500));
  } else if (state === "long-loading") {
    await new Promise((r) => setTimeout(r, 9000));
  }

  if (state === "error") {
    return new Response(
      JSON.stringify({ error: "PDF ayrıştırma servisi yanıt vermedi (422)." }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );
  }

  if (parsed.pathname === "/api/cv") {
    if (state === "empty") {
      return new Response(JSON.stringify({ applications: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    const apps = getSeedApplications();
    const result =
      state === "partial" ? apps.map((a) => ({ ...a, salary: null })) : apps;
    return new Response(JSON.stringify({ applications: result }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  const analyzeMatch = parsed.pathname.match(/^\/api\/cv\/([^/]+)\/analyze$/);
  if (analyzeMatch && init?.method === "POST") {
    const id = analyzeMatch[1];
    const found = getSeedApplications().find((a) => a.id === id) ?? getSeedApplications()[0];
    return new Response(
      JSON.stringify({
        ok: true,
        application: { ...found, score: Math.min(99, found.score + 3) },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  }

  const detailMatch = parsed.pathname.match(/^\/api\/cv\/([^/]+)$/);
  if (detailMatch) {
    if (state === "empty") {
      return new Response(JSON.stringify({ application: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    const found = getSeedApplications().find((a) => a.id === detailMatch[1]);
    if (!found) {
      return new Response(JSON.stringify({ error: "Başvuru bulunamadı" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ application: found }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ error: "Bilinmeyen uç nokta" }), {
    status: 404,
    headers: { "Content-Type": "application/json" },
  });
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const state = getRequestedMockState();
  const sep = path.includes("?") ? "&" : "?";
  const url = state ? `${path}${sep}state=${encodeURIComponent(state)}` : path;

  try {
    const res = await fetch(url, init);
    const ctype = res.headers.get("content-type") ?? "";
    if (ctype.includes("application/json")) {
      return res;
    }
    // Service worker inactive (e.g., preview server returned index.html SPA fallback):
    return await fallbackMockFetch(url, init);
  } catch {
    return await fallbackMockFetch(url, init);
  }
}

export async function fetchApplications(): Promise<Application[]> {
  const res = await apiFetch("/api/cv");
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Veri alınamadı" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { applications?: Application[]; items?: Application[] };
  if (Array.isArray(data.applications)) return data.applications;
  if (Array.isArray(data.items)) return data.items;
  return [];
}

export async function fetchApplicationById(id: string): Promise<Application | null> {
  const res = await apiFetch(`/api/cv/${encodeURIComponent(id)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Başvuru detayı alınamadı" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { application?: Application | null; items?: Application[] };
  if ("application" in data) {
    return data.application ?? null;
  }
  if (Array.isArray(data.items) && data.items.length === 0) {
    return null;
  }
  return null;
}

export async function analyzeApplication(id: string): Promise<Application> {
  const res = await apiFetch(`/api/cv/${encodeURIComponent(id)}/analyze`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Analiz başarısız" }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  const data = (await res.json()) as { application: Application };
  return data.application;
}
