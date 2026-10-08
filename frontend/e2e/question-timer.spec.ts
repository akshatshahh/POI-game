import { expect, test, type Page } from "@playwright/test";

const FIRST_QUESTION_ID = "00000000-0000-4000-8000-000000000101";
const SECOND_QUESTION_ID = "00000000-0000-4000-8000-000000000102";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "timer-check",
  email: "timer-check@example.com",
  display_name: "Timer Check",
  avatar_url: null,
  score: 5,
  answers_count: 1,
  is_admin: false,
  created_at: "2026-09-23T12:00:00Z",
};

function question(id: string, placePrefix: string) {
  return {
    question_id: id,
    gps_point: {
      lat: 34.02065,
      lon: -118.28543,
      timestamp: "2026-09-23T19:30:00Z",
      weekday: "Wednesday",
      local_date: "2026-09-23",
      local_time: "12:30 PM",
    },
    candidates: [
      { id: `${placePrefix}-1`, name: `${placePrefix} Cafe`, category: "cafe", lat: 34.0208, lon: -118.2852 },
      { id: `${placePrefix}-2`, name: `${placePrefix} Library`, category: "library", lat: 34.0204, lon: -118.2856 },
      { id: `${placePrefix}-3`, name: `${placePrefix} Store`, category: "retail", lat: 34.0207, lon: -118.2857 },
    ],
    prior_answers: 0,
  };
}

async function mockGame(
  page: Page,
  answersCount: number,
  exclusions: string[],
): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    const url = new URL(route.request().url());
    const headers = {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4317",
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "content-type",
      "content-type": "application/json",
    };

    if (url.pathname === "/auth/me") {
      await route.fulfill({
        status: 200,
        headers,
        json: { ...user, answers_count: answersCount },
      });
      return;
    }
    if (url.pathname === "/game/next-question") {
      const excludedId = url.searchParams.get("exclude_question_id");
      if (excludedId) exclusions.push(excludedId);
      await route.fulfill({
        status: 200,
        headers,
        json: excludedId
          ? question(SECOND_QUESTION_ID, "Second")
          : question(FIRST_QUESTION_ID, "First"),
      });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

test("Next Question click does not send the click event as a question ID", async ({ page }) => {
  const exclusions: string[] = [];
  await mockGame(page, 1, exclusions);
  await page.route("**/game/answer", (route) => route.fulfill({
    status: 200,
    headers: {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4317",
    },
    json: {
      id: "00000000-0000-4000-8000-000000000301",
      question_id: FIRST_QUESTION_ID,
      selected_poi_id: "First-1",
      selected_poi_ids: ["First-1"],
      score_awarded: 5,
      created_at: "2026-10-07T12:00:00Z",
    },
  }));
  await page.goto("/play");
  await page.locator(".hud-candidate-grid button").first().click();
  await page.getByRole("button", { name: "Submit Answer", exact: true }).click();
  const nextRequest = page.waitForRequest((request) => new URL(request.url()).pathname === "/game/next-question");
  await page.getByRole("button", { name: /Next Question/ }).click();
  expect(new URL((await nextRequest).url()).searchParams.has("exclude_question_id")).toBe(false);
  expect(exclusions).toEqual([]);
});

for (const entry of ["Logout", "Feedback"]) {
test(`pauses the question timer while ${entry} feedback is open`, async ({ page }) => {
  const exclusions: string[] = [];
  await page.clock.install();
  await mockGame(page, 1, exclusions);
  await page.goto("/play");
  await expect(page.getByRole("timer")).toContainText("1:00");
  expect(await page.evaluate(() => {
    const header = document.querySelector(".navbar")!.getBoundingClientRect();
    const game = document.querySelector(".main-content--play")!.getBoundingClientRect();
    return Math.abs(game.top - header.bottom) < 2 && Math.abs(game.bottom - window.innerHeight) < 2;
  })).toBe(true);
  await page.clock.fastForward(10_000);
  await page.getByRole("button", { name: entry, exact: true }).click();
  await page.clock.fastForward(70_000);
  await expect(page.getByRole("timer")).toContainText("0:50");
  expect(exclusions).toEqual([]);
  await page.getByRole("button", { name: entry === "Logout" ? "Keep playing" : "Close", exact: true }).click();
  await page.clock.fastForward(10_000);
  await expect(page.getByRole("timer")).toContainText("0:40");
});
}

test("loads a different question when the 60-second timer expires", async ({ page }) => {
  const exclusions: string[] = [];

  await page.clock.install();
  await mockGame(page, 1, exclusions);

  await page.goto("/play");

  const timer = page.getByRole("timer");
  await expect(timer).toContainText("1:00");
  await expect(page.getByText("First Cafe")).toBeVisible();

  await page.clock.fastForward(50_000);
  await expect(timer).toContainText("0:10");
  await expect(timer).toHaveClass(/hud-question-timer--urgent/);

  await page.clock.fastForward(10_000);
  await expect(page.getByText("Second Cafe")).toBeVisible();
  await expect(timer).toContainText("1:00");
  expect(exclusions).toContain(FIRST_QUESTION_ID);
});

test("does not run the question timer during the first-time tutorial", async ({ page }) => {
  const exclusions: string[] = [];

  await page.clock.install();
  await mockGame(page, 0, exclusions);
  await page.goto("/play");

  const timer = page.getByRole("timer");
  await expect(page.getByRole("heading", { name: "Visit time" })).toBeVisible();
  await page.clock.fastForward(60_000);
  await expect(timer).toContainText("1:00");
  await expect(page.getByText("First Cafe")).toBeVisible();
  expect(exclusions).toEqual([]);

  await page.getByRole("button", { name: "Skip tutorial" }).click();
  await page.clock.fastForward(1_000);
  await expect(timer).toContainText("0:59");

  await page.clock.fastForward(59_000);
  await expect(page.getByText("Second Cafe")).toBeVisible();
  expect(exclusions).toContain(FIRST_QUESTION_ID);
});
