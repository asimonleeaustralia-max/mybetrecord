import { test, expect } from "@playwright/test";
import { loginViaUi } from "../helpers.js";

const VIEWPORTS = [
  { width: 320, height: 568 },
  { width: 375, height: 667 },
  { width: 414, height: 896 },
];

async function mainOverflows(page) {
  return page.locator("#main").evaluate((el) => {
    if (!el || el.clientWidth === 0) return false;
    return el.scrollWidth > el.clientWidth + 1;
  });
}

test.describe("mobile layout", () => {
  for (const viewport of VIEWPORTS) {
    test(`no horizontal overflow at ${viewport.width}px`, async ({ page, request, baseURL }) => {
      await page.setViewportSize(viewport);
      await page.goto("/");
      const landingOverflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
      );
      expect(landingOverflow).toBe(false);

      await loginViaUi(page, request, baseURL, "layout");

      for (const hash of ["#/bets", "#/new", "#/reports", "#/settings"]) {
        await page.goto(`/app/${hash}`);
        await expect(page.locator("#main")).toBeVisible({ timeout: 15_000 });
        const overflow = await mainOverflows(page);
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
