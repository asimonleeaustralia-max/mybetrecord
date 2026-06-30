import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.BASE_URL || "http://localhost:8080";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  timeout: 60_000,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "pixel-5", use: { ...devices["Pixel 5"] } },
    { name: "iphone-12", use: { ...devices["iPhone 12"] } },
    { name: "iphone-se", use: { ...devices["iPhone SE"] } },
    { name: "webkit-desktop", use: { ...devices["Desktop Safari"] } },
  ],
});
