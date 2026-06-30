import { test, expect } from "@playwright/test";
import { registerAndLogin, uniqueEmail } from "../helpers.js";

const VIEWPORTS = [
  { width: 320, height: 568 },
  { width: 375, height: 667 },
  { width: 414, height: 896 },
];

test.describe("mobile layout", () => {
  for (const viewport of VIEWPORTS) {
    test(`no horizontal overflow at ${viewport.width}px`, async ({ page, request, baseURL }) => {
      await page.setViewportSize(viewport);
      await page.goto("/");
      const landingOverflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth
      );
      expect(landingOverflow).toBe(false);

      const email = uniqueEmail("layout");
      await registerAndLogin(request, baseURL, email);
      await page.goto("/app/#/login");
      await page.locator("#loginForm input[name=email]").fill(email);
      await page.locator("#loginForm input[name=password]").fill("password123");
      await page.locator("#loginForm button[type=submit]").click();
      await expect(page.locator(".topbar")).toBeVisible({ timeout: 15_000 });

      for (const hash of ["#/bets", "#/new", "#/reports", "#/settings"]) {
        await page.goto(`/app/${hash}`);
        await page.waitForTimeout(300);
        const overflow = await page.evaluate(() =>
          document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
        );
        expect(overflow, `overflow on ${hash} at ${viewport.width}px`).toBe(false);
      }

      await expect(page.locator(".app-chrome")).toBeVisible();
      await expect(page.locator(".tabs .tab").first()).toBeVisible();
    });
  }

  test("marketing header uses class-based mobile layout", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");
    await expect(page.locator(".m-header--with-end")).toBeVisible();
    await expect(page.locator(".m-nav")).toBeVisible();
  });
});
