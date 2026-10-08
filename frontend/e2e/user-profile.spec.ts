import { expect, test, type Page } from "@playwright/test";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "hitansh_surani",
  email: "hsurani@usc.edu",
  display_name: "Hitansh Surani",
  avatar_url: "https://images.example.test/avatar.png",
  score: 90,
  answers_count: 7,
  is_admin: false,
  created_at: "2026-08-26T12:00:00Z",
};

async function mockUser(page: Page): Promise<void> {
  await page.route("https://images.example.test/**", (route) => route.abort());
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const headers = {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4317",
      "content-type": "application/json",
    };

    if (path === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: user });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

test("opens complete account details from the navbar username", async ({ page }) => {
  await mockUser(page);
  await page.goto("/");

  const trigger = page.getByRole("button", { name: "View profile for Hitansh Surani" });
  await expect(trigger).toBeVisible();
  await trigger.click();

  const dialog = page.getByRole("dialog", { name: "Hitansh Surani" });
  await expect(dialog).toBeVisible();
  await expect(dialog.locator(".user-profile-avatar--fallback")).toHaveText("HS");
  await expect(dialog.getByText("hitansh_surani", { exact: true })).toBeVisible();
  await expect(dialog.getByText("hsurani@usc.edu", { exact: true })).toBeVisible();
  await expect(dialog.getByText("90", { exact: true })).toBeVisible();
  await expect(dialog.getByText("7", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Questions answered", { exact: true })).toBeVisible();
  await expect(dialog.getByText("Player", { exact: true })).toBeVisible();
  await expect(dialog.locator("time")).toHaveAttribute("datetime", user.created_at);

  const bounds = await dialog.boundingBox();
  const viewport = page.viewportSize();
  expect(bounds).not.toBeNull();
  expect(viewport).not.toBeNull();
  if (bounds && viewport) {
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.y).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height + 1);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(trigger).toBeFocused();

  await trigger.click();
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(trigger).toBeFocused();
});
