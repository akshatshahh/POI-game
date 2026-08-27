import { expect, test, type Locator, type Page } from "@playwright/test";

const USER_ID = "00000000-0000-4000-8000-000000000001";

const user = {
  id: USER_ID,
  username: "tutorial-check",
  email: "tutorial-check@example.com",
  display_name: "Tutorial Check",
  avatar_url: null,
  score: 0,
  answers_count: 0,
  is_admin: false,
  created_at: "2026-08-26T12:00:00Z",
};

const question = {
  question_id: "00000000-0000-4000-8000-000000000002",
  gps_point: {
    lat: 34.02065,
    lon: -118.28543,
    timestamp: "2026-08-26T19:30:00Z",
    weekday: "Wednesday",
    local_date: "2026-08-26",
    local_time: "12:30 PM",
  },
  candidates: [
    {
      id: "poi-1",
      name: "USC Village Dining Hall",
      category: "restaurant",
      lat: 34.02082,
      lon: -118.28522,
    },
    {
      id: "poi-2",
      name: "Doheny Memorial Library",
      category: "library",
      lat: 34.02041,
      lon: -118.28561,
    },
    {
      id: "poi-3",
      name: "USC Bookstore",
      category: "retail",
      lat: 34.02072,
      lon: -118.28572,
    },
  ],
  prior_answers: 1,
};

async function mockApi(page: Page): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const headers = {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4173",
      "content-type": "application/json",
    };

    if (pathname === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: user });
      return;
    }
    if (pathname === "/game/next-question") {
      await route.fulfill({ status: 200, headers, json: question });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

async function expectInsideViewport(page: Page, locator: Locator): Promise<void> {
  const viewport = page.viewportSize();

  expect(viewport).not.toBeNull();
  if (!viewport) return;

  await expect
    .poll(async () => {
      const box = await locator.boundingBox();
      return Boolean(
        box &&
          box.x >= 0 &&
          box.y >= 0 &&
          box.x + box.width <= viewport.width + 1 &&
          box.y + box.height <= viewport.height + 1,
      );
    })
    .toBe(true);
}

async function expectHighlighted(
  page: Page,
  targetSelector: string,
): Promise<void> {
  const target = page.locator(targetSelector).first();
  const spotlight = page.locator(".tutorial-spotlight");

  await expect(target).toBeVisible();
  await expect(spotlight).toBeVisible();
  await expectInsideViewport(page, page.locator(".tutorial-card"));
  await expectInsideViewport(page, spotlight);

  await expect
    .poll(async () => {
      const targetBox = await target.boundingBox();
      const spotlightBox = await spotlight.boundingBox();
      return Boolean(
        targetBox &&
          spotlightBox &&
          spotlightBox.x <= targetBox.x &&
          spotlightBox.y <= targetBox.y &&
          spotlightBox.x + spotlightBox.width >= targetBox.x + targetBox.width &&
          spotlightBox.y + spotlightBox.height >= targetBox.y + targetBox.height,
      );
    })
    .toBe(true);
}

test("first-time tutorial explains and highlights the full game flow", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  await mockApi(page);

  await page.goto("/play");

  const card = page.locator(".tutorial-card");
  await expect(card).toBeVisible();
  await expect(page.getByRole("heading", { name: "Welcome to POI Game" })).toBeVisible();
  await expect(page.locator(".tutorial-progress-segment")).toHaveCount(5);
  await expectInsideViewport(page, card);

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("heading", { name: "Use the visit time" })).toBeVisible();
  await expectHighlighted(page, '[data-tutorial="visit-time"]');

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("heading", { name: "Start at the red pin" })).toBeVisible();
  await expectHighlighted(page, ".gps-location-marker");

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("heading", { name: "Choose the most likely place" })).toBeVisible();
  await expectHighlighted(page, '[data-tutorial="poi-choices"]');

  await page.getByRole("button", { name: "Next" }).click();
  await expect(
    page.getByRole("heading", { name: "How the final POI is decided" }),
  ).toBeVisible();
  await expectHighlighted(page, '[data-tutorial="submit-answer"]');

  await page.getByRole("button", { name: "Start playing" }).click();
  await expect(card).toBeHidden();
  await expect
    .poll(() =>
      page.evaluate(
        (key) => window.localStorage.getItem(key),
        `poi-game:tutorial:v1:${USER_ID}`,
      ),
    )
    .toBe("complete");

  await page.reload();
  await expect(page.locator(".tutorial-card")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(browserErrors).toEqual([]);
});
