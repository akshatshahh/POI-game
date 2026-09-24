import { expect, test, type Locator, type Page } from "@playwright/test";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "leaderboard-check",
  email: "leaderboard-check@example.com",
  display_name: "Leaderboard Check",
  avatar_url: null,
  score: 130,
  answers_count: 20,
  is_admin: false,
  created_at: "2026-09-23T12:00:00Z",
};

const entries = [
  { rank: 1, display_name: "Gaston L", avatar_url: null, score: 130, answers_count: 20 },
  { rank: 2, display_name: "Serena", avatar_url: null, score: 110, answers_count: 10 },
  { rank: 3, display_name: "Akshat Shah", avatar_url: null, score: 90, answers_count: 7 },
];

async function mockApi(page: Page): Promise<void> {
  await page.route("http://localhost:8000/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const headers = {
      "access-control-allow-credentials": "true",
      "access-control-allow-origin": "http://localhost:4317",
      "content-type": "application/json",
    };

    if (pathname === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: user });
      return;
    }
    if (pathname === "/leaderboard") {
      await route.fulfill({ status: 200, headers, json: entries });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

async function expectRightEdgesAligned(header: Locator, value: Locator): Promise<void> {
  const [headerBox, valueBox] = await Promise.all([header.boundingBox(), value.boundingBox()]);

  expect(headerBox).not.toBeNull();
  expect(valueBox).not.toBeNull();
  if (!headerBox || !valueBox) return;

  expect(Math.abs(headerBox.x + headerBox.width - (valueBox.x + valueBox.width))).toBeLessThan(1);
}

test("aligns leaderboard answer and score columns", async ({ page }) => {
  await mockApi(page);
  await page.goto("/leaderboard");

  const answersHeader = page.getByRole("columnheader", { name: "Answers" });
  const scoreHeader = page.getByRole("columnheader", { name: "Score" });
  const firstAnswers = page.locator("tbody .col-answers").first();
  const firstScore = page.locator("tbody .col-score").first();

  await expect(firstAnswers).toHaveText("20");
  await expect(firstScore).toHaveText("130");
  await expect(answersHeader).toHaveCSS("text-align", "right");
  await expect(scoreHeader).toHaveCSS("text-align", "right");
  await expectRightEdgesAligned(answersHeader, firstAnswers);
  await expectRightEdgesAligned(scoreHeader, firstScore);
});
