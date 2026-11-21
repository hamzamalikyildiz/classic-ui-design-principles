# Sample Data & Seeding Reference

## 1. Core Principle — No Screenshots on an Empty Database

An empty database screenshot only tests the empty state. Before running `render.py` or reviewing visual hierarchy, seed realistic data that exercises the populated view and every priority state (`reference/states.md`). Render empty states deliberately via state switches or route mocks, never by accident.

## 2. Realistic Data Recipe (Checklist)

- **Believable domain names & locales:** Real-sounding people, companies, and titles (`Çağla İnanç`, `Şahin Öztürk`, `İK Uzmanı`) to test font glyphs and uppercase folding (`i -> İ`, `ı -> I` per `reference/typography-locale.md`).
- **Stress-test edge cases in the same list:** One very long title/name (`75+` chars, testing truncation/wrapping), zero (`0`), large numbers (`1,284,950`), one optional field missing/`null` (partial-data fallback `—` with `aria-label="Metric pending"`), and emoji/special punctuation (`C# / .NET`, `±4.2%`, `₺`, `🎯`).
- **Time distribution:** Today (`"14 min ago"`), yesterday, last month (`"18 Oct"`), and an archived date (`"12 Jan 2024"`) to test `Intl` relative/date formatting.
- **Status mix:** `draft`, `active`/`in-review`, `completed`/`accepted`, and `failed`/`needs-action` in the same view so semantic badges and filters appear together.

## 3. Seeding & Mocking Techniques

**SQL seed template (idempotent `INSERT ... ON CONFLICT`):**
```sql
INSERT INTO applications (id, candidate, role, company, score, salary, status) VALUES
  ('app_01', 'Çağla İnanç', 'Senior Product Designer', 'Kovan', 73, 1284950, 'accepted'),
  ('app_02', 'Şahin Öztürk', 'Principal Distributed Systems & Reliability Architect (EMEA)', 'Borusan', 69, NULL, 'in_review')
ON CONFLICT (id) DO UPDATE SET score = EXCLUDED.score, salary = EXCLUDED.salary, status = EXCLUDED.status;
```

**Typed JSON fixture (`seed.json` shared between app and tests):**
```json
{
  "applications": [
    { "id": "app_01", "candidate": "Çağla İnanç", "role": "Senior Product Designer", "company": "Kovan", "score": 73, "salary": 1284950, "status": "accepted", "updatedAt": "2026-11-21T18:12:00Z" },
    { "id": "app_02", "candidate": "Şahin Öztürk", "role": "Principal Distributed Systems & Reliability Architect", "company": "Borusan", "score": 69, "salary": null, "status": "in_review", "updatedAt": "2026-11-20T16:40:00Z" }
  ]
}
```

**MSW (`msw` `http.get/post`) handlers (`?state=empty|error|long-loading`):**
```ts
import { http, HttpResponse, delay } from "msw";
import seed from "./seed.json";
export const handlers = [
  http.get("/api/applications", async ({ request }) => {
    const s = new URL(request.url).searchParams.get("state") ?? request.headers.get("x-mock-state");
    if (s === "long-loading") await delay(4500);
    if (s === "error") return HttpResponse.json({ error: "Could not parse PDF — password-protected." }, { status: 422 });
    if (s === "empty") return HttpResponse.json({ applications: [] });
    if (s === "partial") return HttpResponse.json({ applications: seed.applications.map(a => ({ ...a, salary: null })) });
    return HttpResponse.json(seed);
  }),
  http.post("/api/recommendations/:id/accept", () => HttpResponse.json({ ok: true, score: 73 })),
];
```

**Next.js Route Handler / Server Action offline DB fallback:**
```ts
import { NextResponse } from "next/server";
import seed from "@/fixtures/seed.json";
export async function GET(req: Request) {
  const s = new URL(req.url).searchParams.get("state");
  if (s === "empty") return NextResponse.json({ applications: [] });
  if (s === "error") return NextResponse.json({ error: "Scoring service timed out." }, { status: 503 });
  try {
    const rows = await db.application.findMany({ orderBy: { updatedAt: "desc" } });
    return NextResponse.json({ applications: rows.length ? rows : seed.applications });
  } catch {
    return NextResponse.json({ applications: seed.applications, fallback: true });
  }
}
```

**`render.py --routes routes.json` (`mock_body` / `states`) integration:**
```json
{
  "base_url": "http://localhost:3000", "viewports": ["desktop", "mobile"],
  "routes": [{
    "name": "cv-list", "path": "/cv", "wait_for": "[data-ready]",
    "mock_body": { "/api/applications": "fixtures/seed.json" },
    "states": ["default", "empty", "partial", "error", "loading", "long-loading"]
  }]
}
```

## 4. Canonical Reference Dataset (CV Optimization App Example)

Used by `examples/app-demo`:

| ID | Candidate | Role Title | Company | Score | Salary | Status | Updated |
|---|---|---|---|---|---|---|---|
| `app_01` | Çağla İnanç | Senior Product Designer | Kovan | `73` | `1,284,950` | `accepted` | `14 min ago` |
| `app_02` | Şahin Öztürk | Principal Distributed Systems & Platform Reliability Architect (EMEA / İstanbul) | Borusan | `69` | `null` (`—`) | `in_review` | `Yesterday` |
| `app_03` | Elif Karakoç | İK Uzmanı & Yetenek Kazanımı Lideri | Arçelik | `84` | `920,000` | `draft` | `18 Oct` |
| `app_04` | Mertcan Yılmaz | Frontend Platform Engineer | Getir | `0` | `1,050,000` | `failed` | `12 Jan 2024` |

- **Score History (`69 -> 73` across 3 revisions on `app_01`):** `rev_1` (`18 Oct`: `64`) -> `rev_2` (`Yesterday`: `69`) -> `rev_3` (`14 min ago`: `73`, count-up ring `69 -> 73`).
- **6 AI Recommendations (2 accepted, 3 pending, 1 dismissed):** *Accepted:* `rec_1` (`+2`, `"Quantify design-system adoption"`), `rec_2` (`+2`, `"Add WCAG AA audit outcome"`). *Pending:* `rec_3` (`+5`, `"Align bullets with OKLCH tokens"`), `rec_4` (`+3`, `"Highlight Code Connect & CI"`), `rec_5` (`+2`, `"Replace passive verbs"`). *Dismissed:* `rec_6` (`0`, `"Add basic HTML/CSS badge"`).
- **3 Interview Questions (1 unanswered partial state):** `q_1` (*Answered*, `4.5/5`: `"How did you migrate hex values to semantic tokens?"`), `q_2` (*Answered*, `4.0/5`: `"Describe a brand vs WCAG AA contrast fix."`), `q_3` (*Unanswered — partial*: `"How do you measure component adoption?"`, `answer: null`, score `—`, CTA `"Record answer"`).
