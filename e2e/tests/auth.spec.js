import { test, expect } from "@playwright/test";
import { loginViaUi } from "../helpers.js";

test.describe("auth", () => {
  test("register, login, and sign out", async ({ page, request, baseURL }) => {
    await loginViaUi(page, request, baseURL, "auth");

    await page.locator("#logoutBtn").click();
    await expect(page.locator("#auth")).toBeVisible({ timeout: 10_000 });
  });
});
