const PASSWORD = "password123";

export async function registerAndLogin(request, baseURL, email) {
  const register = await request.post(`${baseURL}/auth/register`, {
    data: { email, password: PASSWORD, timezone: "UTC" },
  });
  if (!register.ok()) {
    throw new Error(`register failed: ${register.status()} ${await register.text()}`);
  }
  const body = await register.json();
  const token = body.verification_token;
  if (!token) {
    throw new Error("verification_token missing — is ENVIRONMENT=development?");
  }
  const verify = await request.post(`${baseURL}/auth/register/verify`, {
    data: { token },
  });
  if (!verify.ok()) {
    throw new Error(`verify failed: ${verify.status()} ${await verify.text()}`);
  }
  const { access_token } = await verify.json();
  return access_token;
}

export function uniqueEmail(prefix = "e2e") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}
