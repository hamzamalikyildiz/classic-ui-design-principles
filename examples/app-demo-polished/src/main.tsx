import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

async function enableMocking() {
  if (import.meta.env.VITE_DISABLE_MSW === "true") {
    return;
  }
  try {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      onUnhandledRequest: "bypass",
      quiet: true,
    });
  } catch {
    // Fallback mock fetch in src/lib/api.ts handles /api/* when SW cannot register
  }
}

void enableMocking().finally(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
