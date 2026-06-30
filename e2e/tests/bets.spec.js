import { test, expect } from "@playwright/test";
import { registerAndLogin, uniqueEmail } from "../helpers.js";

async function login(page, request, baseURL) {
  const email = uniqueEmail("bets");
  await registerAndLogin(request, baseURL, email);
  await page.goto("/app/#/login");
  await page.locator("#loginForm input[name=email]").fill(email);
  await page.locator("#loginForm input[name=password]").fill("password123");
  await page.locator("#loginForm button[type=submit]").click();
  await expect(page.locator(".topbar")).toBeVisible({ timeout: 15_000 });
  return email;
}

test.describe("bets", () => {
  test("record a bet and see it in the ledger", async ({ page, request, baseURL }) => {
    await login(page, request, baseURL);

    await page.goto("/app/#/new");
    await expect(page.locator("#betForm")).toBeVisible({ timeout: 10_000 });

    await page.locator("#betForm input[name=sport]").fill("Football");
    await page.locator("#betForm input[name=event]").fill("Team A vs Team B");
    await page.locator("#betForm input[name=selection]").fill("Team A");
    await page.locator("#betForm input[name=odds]").fill("2.50");
    await page.locator("#betForm input[name=stake]").fill("50");
    await page.locator("#betForm button[type=submit]").click();

    await page.waitForURL(/#\/bets/, { timeout: 15_000 });
    await expect(page.locator("#betsBody")).toContainText("Team A", { timeout: 10_000 });
    await expect(page.locator("#betsBody")).toContainText("2.50");
  });
});
