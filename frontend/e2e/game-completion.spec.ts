import { expect, test, type Page } from "@playwright/test";

const headers = {
  "access-control-allow-credentials": "true",
  "access-control-allow-origin": "http://localhost:4317",
  "access-control-allow-methods": "GET, POST, DELETE, OPTIONS",
  "access-control-allow-headers": "content-type",
  "content-type": "application/json",
};

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "campaign-player",
  email: "player@example.com",
  display_name: "Campaign Player",
  avatar_url: null,
  score: 180,
  answers_count: 12,
  is_admin: false,
  created_at: "2026-09-23T12:00:00Z",
};

interface CompletedGameOptions {
  answersCount?: number;
  nextStatus?: 404 | 410;
  subscribed?: boolean;
  failedSaves?: number;
}

async function mockCompletedGame(page: Page, options: CompletedGameOptions = {}) {
  const answersCount = options.answersCount ?? user.answers_count;
  const nextStatus = options.nextStatus ?? 410;
  let subscribed = options.subscribed ?? false;
  let failedSaves = options.failedSaves ?? 0;
  let submittedEmail = "";
  let removeRequests = 0;

  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;

    if (pathname === "/auth/me") {
      await route.fulfill({
        status: 200,
        headers,
        json: { ...user, answers_count: answersCount },
      });
      return;
    }
    if (pathname === "/game/next-question") {
      await route.fulfill({
        status: nextStatus,
        headers,
        json: {
          detail: nextStatus === 410
            ? "You have completed every available question in this campaign."
            : "No more questions available. Check back later!",
        },
      });
      return;
    }
    if (pathname === "/campaign-subscriptions/me" && request.method() === "GET") {
      await route.fulfill({
        status: 200,
        headers,
        json: {
          subscribed,
          email: subscribed ? user.email : null,
          created_at: subscribed ? "2026-10-29T12:00:00Z" : null,
        },
      });
      return;
    }
    if (pathname === "/campaign-subscriptions/me" && request.method() === "DELETE") {
      subscribed = false;
      removeRequests += 1;
      await route.fulfill({ status: 204, headers });
      return;
    }
    if (pathname === "/campaign-subscriptions" && request.method() === "POST") {
      if (failedSaves > 0) {
        failedSaves -= 1;
        await route.fulfill({
          status: 500,
          headers,
          json: { detail: "The notification preference could not be saved" },
        });
        return;
      }
      submittedEmail = (request.postDataJSON() as { email: string }).email;
      subscribed = true;
      await route.fulfill({
        status: 201,
        headers,
        json: {
          id: "00000000-0000-4000-8000-000000000501",
          email: submittedEmail.toLowerCase(),
          created_at: "2026-10-29T12:00:00Z",
        },
      });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });

  return {
    submittedEmail: () => submittedEmail,
    removeRequests: () => removeRequests,
  };
}

test("celebrates campaign completion and saves the account email", async ({ page }) => {
  const requests = await mockCompletedGame(page);
  await page.goto("/play");

  const title = page.getByRole("heading", { level: 1, name: "Congratulations!" });
  await expect(title).toBeVisible();
  await expect(title).toBeFocused();
  await expect(page.getByText("You answered every available question", { exact: false })).toBeVisible();
  await expect(page.getByText("Total score")).toContainText("180");
  await expect(page.locator(".completion-confetti-piece")).toHaveCount(36);

  const email = page.getByLabel("Email address");
  await expect(email).toHaveValue("player@example.com");
  await expect(email).toHaveAttribute("readonly", "");
  await page.getByRole("button", { name: "Notify me" }).click();

  await expect(page.getByRole("heading", { name: "You are on the list" })).toBeVisible();
  await expect(page.getByText("player@example.com")).toBeVisible();
  expect(requests.submittedEmail()).toBe("player@example.com");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("does not congratulate a first-time player when no campaign is available", async ({ page }) => {
  await mockCompletedGame(page, { answersCount: 0, nextStatus: 404 });
  await page.goto("/play");

  await expect(page.getByRole("heading", { name: "No Questions Available" })).toBeVisible();
  await expect(page.getByText("No more questions available", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Congratulations!" })).toHaveCount(0);
});

test("does not treat a generic no-questions response as completion", async ({ page }) => {
  await mockCompletedGame(page, { nextStatus: 404 });
  await page.goto("/play");

  await expect(page.getByRole("heading", { name: "No Questions Available" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Congratulations!" })).toHaveCount(0);
});

test("shows an existing preference and lets the player remove it", async ({ page }) => {
  const requests = await mockCompletedGame(page, { subscribed: true });
  await page.goto("/play");

  await expect(page.getByRole("heading", { name: "You are on the list" })).toBeVisible();
  await page.getByRole("button", { name: "Remove notification" }).click();

  await expect(page.getByRole("heading", { name: "Play the next campaign" })).toBeVisible();
  await expect(page.getByText("Campaign notifications have been removed.")).toBeVisible();
  expect(requests.removeRequests()).toBe(1);
});

test("allows retrying a failed notification save", async ({ page }) => {
  await mockCompletedGame(page, { failedSaves: 1 });
  await page.goto("/play");

  await page.getByRole("button", { name: "Notify me" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "The notification preference could not be saved",
  );

  await page.getByRole("button", { name: "Notify me" }).click();
  await expect(page.getByRole("heading", { name: "You are on the list" })).toBeVisible();
});

test("hides confetti when reduced motion is requested", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockCompletedGame(page);
  await page.goto("/play");

  await expect(page.getByRole("heading", { name: "Congratulations!" })).toBeVisible();
  await expect(page.locator(".completion-confetti-piece").first()).toHaveCSS("display", "none");
});

test("shows the refreshed score after the final answer", async ({ page }) => {
  let answered = false;
  const question = {
    question_id: "00000000-0000-4000-8000-000000000101",
    gps_point: {
      lat: 34.02065,
      lon: -118.28543,
      timestamp: "2026-09-23T19:30:00Z",
      weekday: "Wednesday",
      local_date: "2026-09-23",
      local_time: "12:30 PM",
    },
    candidates: [
      { id: "poi-1", name: "Cafe", category: "cafe", lat: 34.0208, lon: -118.2852 },
      { id: "poi-2", name: "Library", category: "library", lat: 34.0204, lon: -118.2856 },
      { id: "poi-3", name: "Store", category: "retail", lat: 34.0207, lon: -118.2857 },
    ],
    prior_answers: 0,
  };

  await page.route("http://localhost:8000/**", async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;

    if (pathname === "/auth/me") {
      await route.fulfill({
        status: 200,
        headers,
        json: {
          ...user,
          score: answered ? 10 : 5,
          answers_count: answered ? 2 : 1,
        },
      });
      return;
    }
    if (pathname === "/game/next-question") {
      await route.fulfill(answered
        ? {
            status: 410,
            headers,
            json: { detail: "You have completed every available question in this campaign." },
          }
        : { status: 200, headers, json: question });
      return;
    }
    if (pathname === "/game/answer" && request.method() === "POST") {
      answered = true;
      await route.fulfill({
        status: 200,
        headers,
        json: {
          id: "00000000-0000-4000-8000-000000000301",
          question_id: question.question_id,
          selected_poi_id: "poi-1",
          selected_poi_ids: ["poi-1"],
          score_awarded: 5,
          created_at: "2026-10-29T12:00:00Z",
        },
      });
      return;
    }
    if (pathname === "/campaign-subscriptions/me") {
      await route.fulfill({
        status: 200,
        headers,
        json: { subscribed: false, email: null, created_at: null },
      });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });

  await page.goto("/play");
  await page.locator(".hud-candidate-grid button").first().click();
  await page.getByRole("button", { name: "Submit Answer", exact: true }).click();
  await page.getByRole("button", { name: /Next Question/ }).click();

  await expect(page.getByRole("heading", { name: "Congratulations!" })).toBeVisible();
  await expect(page.getByText("Total score")).toContainText("10");
});
