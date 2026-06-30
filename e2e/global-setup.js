/** Poll the proxied readiness endpoint before any browser tests run. */
export default async function globalSetup() {
  const base = process.env.BASE_URL || "http://127.0.0.1:8080";
  const timeoutMs = Number(process.env.WAIT_TIMEOUT || 180) * 1000;
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${base}/readyz`);
      if (res.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error(`Stack not ready at ${base}/readyz after ${timeoutMs / 1000}s`);
}
