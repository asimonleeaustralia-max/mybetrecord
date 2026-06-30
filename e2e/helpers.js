import { expect } from "@playwright/test";

const PASSWORD = "password123";

async function postWithRetry(request, url, data, attempts = 5) {
  let lastError;
  for (let i = 0; i < attempts; i++) {
    const res = await request.post(url, { data });
    if (res.ok() || (res.status() >= 400 && res.status() < 500 && res.status() !== 502 && res.status() !== 503)) {
      return res;
    }
    lastError = new Error(`POST ${url} failed: ${res.status()} ${await res.text()}`);
    await new Promise((r) => setTimeout(r, 2000 * (i + 1)));
  }
  throw lastError;
}

export async function registerAndLogin(request, baseURL, email) {
  const register = await postWithRetry(request, `${baseURL}/auth/register`, {
    email,
    password: PASSWORD,
    timezone: "UTC",
  });
  if (!register.ok()) {
    throw new Error(`register failed: ${register.status()} ${await register.text()}`);
  }
  const body = await register.json();
  const token = body.verification_token;
  if (!token) {
    throw new Error("verification_token missing — is ENVIRONMENT=development?");
  }
  const verify = await postWithRetry(request, `${baseURL}/auth/register/verify`, { token });
  if (!verify.ok()) {
    throw new Error(`verify failed: ${verify.status()} ${await verify.text()}`);
  }
  const { access_token } = await verify.json();
  return access_token;
}

export function uniqueEmail(prefix = "e2e") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** Register via API, then sign in through the SPA login form. */
export async function loginViaUi(page, request, baseURL, prefix = "e2e") {
  const email = uniqueEmail(prefix);
  await registerAndLogin(request, baseURL, email);
  await page.goto("/app/#/login");
  await page.locator("#loginForm input[name=email]").fill(email);
  await page.locator("#loginForm input[name=password]").fill(PASSWORD);
  await page.locator("#loginForm button[type=submit]").click();
  await expect(page.locator(".topbar")).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(/#\/bets/, { timeout: 20_000 });
  return email;
}
