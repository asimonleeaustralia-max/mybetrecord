import { test, expect } from "@playwright/test";
import { loginViaUi } from "../helpers.js";

test.describe("reports", () => {
  test("reports view shows metrics", async ({ page, request, baseURL }) => {
    await loginViaUi(page, request, baseURL, "reports");

    await page.locator('.tab[data-view="reports"]').click();
    await expect(page).toHaveURL(/#\/reports/, { timeout: 10_000 });

    const cards = page.locator("#main #metricCards .card");
    await expect(cards.first()).toBeVisible({ timeout: 20_000 });
    await expect(cards).toHaveCount(5);
    await expect(page.locator("#main .chart-wrap, #main .chart-fallback").first()).toBeVisible({ timeout: 25_000 });
  });
});
