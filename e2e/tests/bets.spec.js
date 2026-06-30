import { test, expect } from "@playwright/test";
import { loginViaUi } from "../helpers.js";

test.describe("bets", () => {
  test("record a bet and see it in the ledger", async ({ page, request, baseURL }) => {
    await loginViaUi(page, request, baseURL, "bets");

    await page.locator('.tab[data-view="new"]').click();
    await expect(page).toHaveURL(/#\/new/, { timeout: 10_000 });
    const form = page.locator("#main #betForm");
    await expect(form).toBeVisible({ timeout: 15_000 });

    await form.locator('input[name="sport"]').fill("Football");
    await form.locator('input[name="event"]').fill("Team A vs Team B");
    await form.locator('input[name="selection"]').fill("Team A");
    await form.locator('input[name="odds"]').fill("2.50");
    await form.locator('input[name="stake"]').fill("50");
    await form.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/#\/bets/, { timeout: 15_000 });
    await expect(page.locator("#main #betsBody")).toContainText("Team A", { timeout: 10_000 });
    await expect(page.locator("#main #betsBody")).toContainText("2.50");
  });
});
