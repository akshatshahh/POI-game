import { expect, test, type Locator, type Page } from "@playwright/test";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "about-check",
  email: "about-check@example.com",
  display_name: "About Check",
  avatar_url: "https://example.com/avatar.png",
  score: 245,
  answers_count: 4,
  is_admin: false,
  created_at: "2026-10-07T12:00:00Z",
};

const headers = {
  "access-control-allow-credentials": "true",
  "access-control-allow-origin": "http://localhost:4317",
  "content-type": "application/json",
};

async function mockSignedOutUser(page: Page): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    await route.fulfill({ status: 401, headers, json: { detail: "Not authenticated" } });
  });
}

async function mockSignedInUser(page: Page): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: user });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

async function expectBelow(upper: Locator, lower: Locator): Promise<void> {
  const upperBox = await upper.boundingBox();
  const lowerBox = await lower.boundingBox();
  expect(upperBox).not.toBeNull();
  expect(lowerBox).not.toBeNull();
  if (!upperBox || !lowerBox) return;
  expect(lowerBox.y).toBeGreaterThan(upperBox.y + upperBox.height);
}

async function expectAboutContent(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { level: 2, name: "About POI Game" })).toBeVisible();
  await expect(page.getByText("Integrated Media Systems Center", { exact: false })).toBeVisible();
  await expect(page.getByText("John Krumm", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "akshatdi@usc.edu" })).toHaveAttribute(
    "href",
    "mailto:akshatdi@usc.edu",
  );
  await expect(page.getByRole("link", { name: "hsurani@usc.edu" })).toHaveAttribute(
    "href",
    "mailto:hsurani@usc.edu",
  );
  await expect(page.getByRole("link", { name: "Contact" })).toHaveAttribute(
    "href",
    "mailto:akshatdi@usc.edu?cc=hsurani@usc.edu&subject=POI%20Game%20Feedback",
  );
  await expect(page.getByRole("link", { name: "About" })).toHaveCount(0);
}

test("places project information below the signed-out login prompt", async ({ page }) => {
  await mockSignedOutUser(page);
  await page.goto("/");

  const loginPrompt = page.locator(".hero-cta-sub");
  const aboutContent = page.locator(".about-content");
  await expect(loginPrompt).toContainText("Already have an account?");
  await expectAboutContent(page);
  await expectBelow(loginPrompt, aboutContent);
});

test("keeps project information on the signed-in home page", async ({ page }) => {
  await mockSignedInUser(page);
  await page.goto("/");

  const continueButton = page.getByRole("link", { name: "Continue Playing" });
  const aboutContent = page.locator(".about-content");
  await expect(continueButton).toBeVisible();
  await expectAboutContent(page);
  await expectBelow(continueButton, aboutContent);
});
