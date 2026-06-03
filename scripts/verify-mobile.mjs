import { mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium, devices } = require(path.resolve(process.cwd(), "apps/web/node_modules/playwright"));

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";
const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8002/api";
const DEMO_USERNAME = process.env.DEMO_USERNAME ?? "admin";
const DEMO_PASSWORD = process.env.DEMO_PASSWORD ?? "admin123";
const SCREENSHOT_DIR = path.resolve(process.cwd(), ".snapshots/mobile-verify");

const PROTECTED_ROUTES = [
  { path: "/command-center", name: "command-center", waitFor: "Command Center" },
  { path: "/board", name: "board", waitFor: "Workflow Tracking" },
  { path: "/incidents", name: "incidents", waitFor: "Incidents" },
  { path: "/reports", name: "reports", waitFor: "Reports & Export" },
  { path: "/admin", name: "admin", waitFor: "Administration" },
  { path: "/tickets/IT-20250049", name: "ticket-detail", waitFor: "Ticket Detail" },
  { path: "/tickets/new", name: "ticket-new", waitFor: "New Ticket" },
];

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function createSession() {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ username: DEMO_USERNAME, password: DEMO_PASSWORD }),
  });
  if (!response.ok) {
    throw new Error(
      `Could not create mobile verification session (${response.status}). Is the API running at ${API_BASE_URL}?`,
    );
  }
  return response.json();
}

async function checkConsoleErrors(page, label) {
  const errors = [];
  page.on("pageerror", (error) => errors.push({ where: label, kind: "pageerror", message: error.message }));
  page.on("console", (message) => {
    if (message.type() === "error") {
      if (message.text().startsWith("Failed to fetch RSC payload")) {
        return;
      }
      errors.push({ where: label, kind: "console.error", message: message.text() });
    }
  });
  return errors;
}

async function loginViaUi(page) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  await page.locator("form#login-form").waitFor({ timeout: 10000 });
  await page.locator('input[name="username"]').fill(DEMO_USERNAME);
  await page.locator('input[name="password"]').fill(DEMO_PASSWORD);
  await Promise.all([
    page.waitForURL((url) => url.pathname === "/command-center", { timeout: 15000 }),
    page.locator('button[type="submit"]').click(),
  ]);
}

async function loginViaStorage(page) {
  const session = await createSession();
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  await page.evaluate((payload) => {
    window.localStorage.setItem("access_token", payload.access_token);
    window.localStorage.setItem("user", JSON.stringify(payload.user));
  }, session);
}

async function captureRoute(page, route, errors) {
  await page.goto(`${BASE_URL}${route.path}`, { waitUntil: "domcontentloaded" });

  if (route.waitFor) {
    try {
      await page.getByText(route.waitFor, { exact: false }).first().waitFor({ state: "attached", timeout: 8000 });
    } catch (error) {
      errors.push({
        where: route.name,
        kind: "missing-content",
        message: `${route.waitFor} did not appear: ${error instanceof Error ? error.message : "unknown"}`,
      });
    }
  }

  await wait(800);

  const screenshotPath = path.join(SCREENSHOT_DIR, `${route.name}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: false });

  const isOnCorrectPath = new URL(page.url()).pathname.startsWith(
    route.path === "/tickets/new" ? "/tickets" : route.path,
  );
  if (!isOnCorrectPath) {
    errors.push({
      where: route.name,
      kind: "wrong-redirect",
      message: `expected ${route.path}, got ${new URL(page.url()).pathname}`,
    });
  }

  return screenshotPath;
}

async function main() {
  await mkdir(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ...devices["iPhone 13"],
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();
  const errors = await checkConsoleErrors(page, "global");

  let loginMethod = "ui";

  try {
    console.log("Logging in through the UI to verify the form works end-to-end...");
    await loginViaUi(page);
  } catch (uiError) {
    console.log(`UI login failed: ${uiError instanceof Error ? uiError.message : uiError}`);
    console.log("Falling back to seeded-token login (UI form regression persisted).");
    await loginViaStorage(page);
    loginMethod = "token";
    errors.push({
      where: "login",
      kind: "ui-fallback",
      message: `UI login did not land on /command-center: ${uiError instanceof Error ? uiError.message : "unknown"}`,
    });
  }

  for (const route of PROTECTED_ROUTES) {
    try {
      const shot = await captureRoute(page, route, errors);
      console.log(`OK  ${route.name} -> ${shot}`);
    } catch (routeError) {
      console.log(`ERR ${route.name}: ${routeError instanceof Error ? routeError.message : routeError}`);
      errors.push({
        where: route.name,
        kind: "capture",
        message: routeError instanceof Error ? routeError.message : String(routeError),
      });
    }
  }

  console.log(`\nLogin method: ${loginMethod}`);
  console.log(`Screenshots:  ${SCREENSHOT_DIR}`);

  if (errors.length) {
    console.log("\nMobile verification found issues:");
    for (const error of errors) {
      console.log(`  - [${error.where}] ${error.kind}: ${error.message}`);
    }
    process.exitCode = 1;
  } else {
    console.log("\nAll mobile protected routes loaded without console errors.");
  }

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
