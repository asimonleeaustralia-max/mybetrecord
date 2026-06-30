import { test, expect } from "@playwright/test";
import { registerAndLogin, uniqueEmail } from "../helpers.js";

test.describe("reports", () => {
  test("reports view shows metrics", async ({ page, request, baseURL }) => {
    const email = uniqueEmail("reports");
    await registerAndLogin(request, baseURL, email);

    await page.goto("/app/#/login");
    await page.locator("#loginForm input[name=email]").fill(email);
    await page.locator("#loginForm input[name=password]").fill("password123");
    await page.locator("#loginForm button[type=submit]").click();
    await expect(page.locator(".topbar")).toBeVisible({ timeout: 15_000 });

    await page.goto("/app/#/reports");
    await expect(page.locator("#metricCards")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("#metricCards .card")).toHaveCount(4);
    await expect(page.locator(".chart-wrap, .chart-fallback").first()).toBeVisible({ timeout: 20_000 });
  });
});
