import { defineConfig, devices } from "@playwright/test";

// UI-сценарии против поднятого стека: make up, затем make e2e.
// Другой адрес стенда: E2E_BASE_URL=http://localhost:8088 npx playwright test
// Браузер: по умолчанию Chromium из `npx playwright install chromium`;
// если скачать его нельзя, подойдёт установленный: E2E_BROWSER_CHANNEL=msedge (или chrome).
const channel = process.env.E2E_BROWSER_CHANNEL;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    locale: "ru-RU",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], ...(channel ? { channel } : {}) },
    },
  ],
});
