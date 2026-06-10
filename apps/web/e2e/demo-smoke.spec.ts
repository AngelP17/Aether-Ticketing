import { expect, test, type Page, type Response } from "@playwright/test";

const expectedTitles = [
  "VPN access fails after password reset",
  "Shared mailbox forwarding rule missing",
  "Printer queue stuck on third floor",
  "ERP approval page timing out",
  "Laptop disk encryption recovery prompt",
  "New hire account missing groups",
  "Phishing report needs review",
  "Warehouse scanner cannot sync inventory",
];

function installPageGuards(page: Page) {
  const failures: string[] = [];

  page.on("pageerror", (error) => {
    failures.push(`pageerror: ${error.message}`);
  });

  page.on("console", (message) => {
    if (message.type() === "error") {
      if (/Failed to load resource: the server responded with a status of (401|403)/i.test(message.text())) {
        return;
      }
      if (message.text().startsWith("Failed to fetch RSC payload")) {
        return;
      }
      failures.push(`console.error: ${message.text()}`);
    }
  });

  page.on("response", (response: Response) => {
    const status = response.status();
    const url = response.url();
    if (status >= 500) {
      failures.push(`server error ${status}: ${url}`);
    }
  });

  return failures;
}

async function loginAsViewer(page: Page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.locator("form#login-form").waitFor();
  await page.locator('input[name="username"]').fill("viewer");
  await page.locator('input[name="password"]').fill("viewer123");
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/command-center", { timeout: 15_000 }),
    page.locator('button[type="submit"]').click(),
  ]);
  await expect(page).toHaveURL(/\/command-center$/);
}

test("viewer login succeeds and weak admin password is rejected", async ({ page }) => {
  const failures = installPageGuards(page);

  await loginAsViewer(page);

  await page.evaluate(() => {
    window.localStorage.clear();
  });
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await page.locator('input[name="username"]').fill("admin");
  await page.locator('input[name="password"]').fill("admin123");
  await page.locator('button[type="submit"]').click();
  await expect(page.getByText(/invalid username or password|invalid credentials|too many failed attempts|timed out/i)).toBeVisible({
    timeout: 20_000,
  });
  await expect(page).toHaveURL(/\/login$/);

  expect(failures).toEqual([]);
});

test("viewer pages render without server errors", async ({ page }) => {
  const failures = installPageGuards(page);
  await loginAsViewer(page);

  const routes = [
    { path: "/command-center", text: /Command Center|Live Queue/i },
    { path: "/board", text: /Workflow Tracking|Board/i },
    { path: "/incidents", text: /Incidents/i },
    { path: "/reports", text: /Reports|Export/i },
    { path: "/tickets/IT-20260001", text: /Ticket Detail|VPN access fails/i },
    { path: "/replay/IT-20260001", text: /Replay|VPN access fails/i },
    { path: "/portal", text: /Portal|ticket/i },
  ];

  for (const route of routes) {
    await page.goto(route.path, { waitUntil: "domcontentloaded" });
    await page.getByText("Checking session...").waitFor({ state: "detached", timeout: 15_000 }).catch(() => null);
    await expect(page.locator("main").getByText(route.text).first()).toBeVisible();
  }

  expect(failures).toEqual([]);
});

test("ticket API exposes only synthetic demo titles", async ({ page, request }) => {
  await loginAsViewer(page);
  const token = await page.evaluate(() => window.localStorage.getItem("access_token"));
  expect(token).toBeTruthy();

  const response = await request.get("/api/tickets?limit=50", {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const rows = Array.isArray(payload) ? payload : payload.tickets ?? [];
  const titles = rows.map((row: { title?: string }) => row.title).sort();
  expect(titles).toEqual([...expectedTitles].sort());
});
