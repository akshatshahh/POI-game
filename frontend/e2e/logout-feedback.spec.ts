import { expect, test } from "@playwright/test";

test("logout feedback can retry without losing input, then saves and logs out", async ({ page }) => {
  let signedIn = true;
  let attempts = 0;
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const headers = { "access-control-allow-origin": "http://localhost:4317", "access-control-allow-credentials": "true" };
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: { ...headers, "access-control-allow-methods": "POST, GET", "access-control-allow-headers": "content-type" } });
    } else if (path === "/auth/me") {
      await route.fulfill({ status: signedIn ? 200 : 401, headers, json: { id: "user", display_name: "Player", score: 0, answers_count: 1 } });
    } else if (path === "/feedback") {
      attempts++;
      expect(route.request().postDataJSON()).toEqual({ rating: 4, comments: "Unclear choices", email: null });
      await route.fulfill({ status: attempts === 1 ? 500 : 201, headers, json: {} });
    } else if (path === "/auth/logout") {
      signedIn = false;
      await route.fulfill({ status: 200, headers, json: {} });
    }
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("1 = least liked · 5 = best")).toBeVisible();
  await expect(page.getByLabel("Comments (optional)")).toHaveAttribute("placeholder", /feedback or questions/);
  const bounds = await page.getByRole("dialog").boundingBox();
  const viewport = page.viewportSize();
  expect(bounds).not.toBeNull();
  expect(viewport).not.toBeNull();
  if (bounds && viewport) {
    expect(Math.abs(bounds.x + bounds.width / 2 - viewport.width / 2)).toBeLessThan(2);
    expect(Math.abs(bounds.y + bounds.height / 2 - viewport.height / 2)).toBeLessThan(2);
  }
  await page.getByRole("radio", { name: "4 stars" }).check();
  await page.getByLabel("Comments (optional)").fill("Unclear choices");
  await page.getByRole("button", { name: "Submit feedback and log out" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("Comments (optional)")).toHaveValue("Unclear choices");
  await page.getByRole("button", { name: "Submit feedback and log out" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(attempts).toBe(2);
});

test("feedback can be cancelled or skipped without sending a rating", async ({ page }) => {
  let signedIn = true;
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    expect(path).not.toBe("/feedback");
    const headers = { "access-control-allow-origin": "http://localhost:4317", "access-control-allow-credentials": "true" };
    if (path === "/auth/logout") signedIn = false;
    await route.fulfill({ status: signedIn || path === "/auth/logout" ? 200 : 401, headers, json: { id: "user", display_name: "Player", score: 0, answers_count: 1 } });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.getByRole("button", { name: "Skip and log out" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
