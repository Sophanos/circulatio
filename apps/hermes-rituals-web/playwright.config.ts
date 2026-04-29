import { defineConfig, devices } from "@playwright/test"

const webPort = process.env.HERMES_RITUAL_WEB_PORT ?? String(31_000 + Math.floor(Math.random() * 900))
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${webPort}`
const completionPort =
  process.env.HERMES_RITUAL_COMPLETION_PORT ?? String(31_990 + Math.floor(Math.random() * 1_000))

process.env.HERMES_RITUAL_WEB_PORT = webPort
process.env.HERMES_RITUAL_COMPLETION_PORT = completionPort

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 7_500 },
  fullyParallel: true,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `bun run dev -- --hostname 127.0.0.1 --port ${webPort}`,
        url: baseURL,
        reuseExistingServer: false,
        timeout: 120_000,
        env: {
          HERMES_RITUAL_COMPLETION_PORT: completionPort,
          HERMES_RITUAL_COMPLETION_URL: `http://127.0.0.1:${completionPort}/complete`
        }
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
})
