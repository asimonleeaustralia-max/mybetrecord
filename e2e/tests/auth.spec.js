import { test, expect } from "@playwright/test";
import { registerAndLogin, uniqueEmail } from "../helpers.js";

test.describe("auth", () => {
  test("register, login, and sign out", async ({ page, request, baseURL }) => {
    const email = uniqueEmail("auth");
    await registerAndLogin(request, baseURL, email);

    await page.goto("/app/#/login");
    await page.locator("#loginForm input[name=email]").fill(email);
    await page.locator("#loginForm input[name=password]").fill("password123");
    await page.locator("#loginForm button[type=submit]").click();

    await expect(page.locator(".topbar")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.tab[data-view="bets"]')).toHaveClass(/is-active/);

    await page.locator("#logoutBtn").click();
    await expect(page.locator("#auth")).toBeVisible({ timeout: 10_000 });
  });
});
