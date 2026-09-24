import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "loading-check",
  email: "loading-check@example.com",
  display_name: "Loading Check",
  avatar_url: null,
  score: 0,
  answers_count: 1,
  is_admin: false,
  created_at: "2026-09-23T12:00:00Z",
};

async function mockLogin(page: Page): Promise<void> {
  let loggedIn = false;

  await page.route("http://localhost:8000/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const headers = {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4317",
      "content-type": "application/json",
    };

    if (pathname === "/auth/me") {
      if (!loggedIn) {
        await route.fulfill({ status: 401, headers, json: { detail: "Not authenticated" } });
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({ status: 200, headers, json: user });
      return;
    }

    if (pathname === "/auth/login") {
      loggedIn = true;
      await route.fulfill({ status: 200, headers, json: { user } });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

test("shows a clear message while completing login", async ({ page }) => {
  await mockLogin(page);
  await page.goto("/login");

  await page.getByLabel("Username or Email").fill("loading-check");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Log In" }).click();

  await expect(page.getByText("Signing you in", { exact: true })).toBeVisible();
  await expect(page.getByText("Please wait while we get your game ready.")).toBeVisible();
  await expect(page.getByRole("status")).toBeVisible();

  await expect(page).toHaveURL("/");
  await expect(page.locator(".hero-stats strong")).toHaveText("Loading Check");
});
