import { delay, http, HttpResponse } from "msw";
import seed from "../../seed.json";
import type { SeedPayload } from "@/types/cv";

const typedSeed = seed as SeedPayload;

function readMockState(request: Request): string | null {
  const url = new URL(request.url);
  return url.searchParams.get("state") ?? request.headers.get("x-mock-state");
}

export const handlers = [
  http.get("/api/cv", async ({ request }) => {
    const state = readMockState(request);
    if (state === "loading") await delay(2500);
    if (state === "long-loading") await delay(9000);
    if (state === "error") {
      return HttpResponse.json(
        { error: "PDF ayrıştırma hatası — belge parola korumalı." },
        { status: 422 },
      );
    }
    if (state === "empty") {
      return HttpResponse.json({ applications: [] });
    }
    if (state === "partial") {
      return HttpResponse.json({
        applications: typedSeed.applications.map((a) => ({ ...a, salary: null })),
      });
    }
    return HttpResponse.json(typedSeed);
  }),

  http.get("/api/cv/:id", async ({ params, request }) => {
    const state = readMockState(request);
    if (state === "loading") await delay(2500);
    if (state === "long-loading") await delay(9000);
    if (state === "error") {
      return HttpResponse.json(
        { error: "Başvuru detayı şu an yüklenemiyor." },
        { status: 500 },
      );
    }
    if (state === "empty") {
      return HttpResponse.json({ application: null });
    }
    const found = typedSeed.applications.find((a) => a.id === params.id);
    if (!found) {
      return HttpResponse.json({ error: "Başvuru bulunamadı" }, { status: 404 });
    }
    return HttpResponse.json({ application: found });
  }),

  http.post("/api/cv/:id/analyze", async ({ params }) => {
    await delay(1200);
    const found =
      typedSeed.applications.find((a) => a.id === params.id) ??
      typedSeed.applications[0];
    return HttpResponse.json({
      ok: true,
      application: {
        ...found,
        score: Math.min(99, found.score + 3),
      },
    });
  }),
];
