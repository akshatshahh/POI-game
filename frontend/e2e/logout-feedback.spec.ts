import { expect, test } from "@playwright/test";

for (const closeMethod of ["Close", "Escape"]) {
test(`${closeMethod} during a pending navbar save does not affect a reopened form`, async ({ page }) => {
  let releaseResponse = () => {};
  const delayedResponse = new Promise<void>((resolve) => { releaseResponse = resolve; });
  let markResponseHandled = () => {};
  const responseHandled = new Promise<void>((resolve) => { markResponseHandled = resolve; });
  const headers = {
    "access-control-allow-origin": "http://localhost:4317",
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "POST, GET, OPTIONS",
    "access-control-allow-headers": "content-type",
  };
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    expect(path).not.toBe("/auth/logout");
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
    } else if (path === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: { id: "user", display_name: "Player", score: 0, answers_count: 1 } });
    } else if (path === "/feedback") {
      await delayedResponse;
      try {
        await route.fulfill({ status: 201, headers, json: {} });
      } finally {
        markResponseHandled();
      }
    }
  });
  await page.goto("/");
  const open = page.getByRole("button", { name: "Feedback", exact: true });
  await open.click();
  await page.getByRole("radio", { name: "3 stars" }).check();
  const requestStarted = page.waitForRequest((request) => request.method() === "POST" && request.url().endsWith("/feedback"));
  await page.getByRole("button", { name: "Submit feedback", exact: true }).click();
  await requestStarted;
  await expect(page.getByRole("button", { name: "Saving…" })).toBeVisible();
  if (closeMethod === "Close") await page.getByRole("button", { name: "Close", exact: true }).click();
  else await page.keyboard.press("Escape");
  await expect(open).toBeFocused();
  await open.click();
  releaseResponse();
  await responseHandled;
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("radio", { name: "3 stars" })).not.toBeChecked();
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Logout", exact: true })).toBeVisible();
});
}

test("navbar feedback saves without logging out and can be reopened or closed", async ({ page }) => {
  await page.clock.install();
  await page.setViewportSize({ width: 320, height: 740 });
  let attempts = 0;
  await page.route("http://localhost:8000/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    expect(path).not.toBe("/auth/logout");
    const headers = {
      "access-control-allow-origin": "http://localhost:4317",
      "access-control-allow-credentials": "true",
      "access-control-allow-methods": "POST, GET, OPTIONS",
      "access-control-allow-headers": "content-type",
    };
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
    } else if (path === "/auth/me") {
      await route.fulfill({ status: 200, headers, json: { id: "user", display_name: "Player", score: 0, answers_count: 1 } });
    } else if (path === "/feedback") {
      attempts++;
      expect(route.request().postDataJSON()).toEqual({ rating: 5, comments: "Helpful map", email: null });
      await route.fulfill({ status: attempts === 1 ? 500 : 201, headers, json: {} });
    }
  });
  await page.goto("/");
  const feedbackButton = page.getByRole("button", { name: "Feedback", exact: true });
  await expect(feedbackButton).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await feedbackButton.click();
  await expect(page.getByRole("heading", { name: "Share your feedback" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Skip and log out" })).toHaveCount(0);
  await page.getByRole("radio", { name: "5 stars" }).check();
  await page.getByLabel("Comments (optional)").fill("Helpful map");
  await page.getByRole("button", { name: "Submit feedback", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("close the form");
  await expect(page.getByLabel("Comments (optional)")).toHaveValue("Helpful map");
  await page.getByRole("button", { name: "Submit feedback", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("status")).toHaveText("Thanks for your feedback.");
  await page.clock.fastForward(5100);
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Logout", exact: true })).toBeVisible();
  await feedbackButton.click();
  await expect(page.getByRole("radio", { name: "5 stars" })).not.toBeChecked();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(feedbackButton).toBeFocused();
  await feedbackButton.click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(attempts).toBe(2);
});

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
  await expect(page.locator(".feedback-stars label")).toHaveText(["☆", "☆", "☆", "☆", "☆"]);
  for (const rating of [1, 3, 5, 2]) {
    await page.getByRole("radio", { name: `${rating} ${rating === 1 ? "star" : "stars"}`, exact: true }).check();
    await expect(page.locator(".feedback-stars label")).toHaveText(
      [1, 2, 3, 4, 5].map((star) => star <= rating ? "★" : "☆"),
    );
    await expect(page.locator(".feedback-stars input:checked")).toHaveCount(1);
  }
  const actionStyles = await page.locator(".feedback-actions button").evaluateAll((buttons) => buttons.map((button) => {
    const style = getComputedStyle(button);
    return { background: style.backgroundColor, color: style.color };
  }));
  expect(new Set(actionStyles.map((style) => style.background)).size).toBe(3);
  expect(actionStyles.every((style) => style.color === "rgb(23, 32, 51)")).toBe(true);
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
  await page.setViewportSize({ width: 320, height: 740 });
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
  const dialog = await page.getByRole("dialog").boundingBox();
  expect(dialog).not.toBeNull();
  if (dialog) {
    expect(dialog.x).toBeGreaterThanOrEqual(0);
    expect(dialog.x + dialog.width).toBeLessThanOrEqual(320);
    expect(dialog.y + dialog.height).toBeLessThanOrEqual(740);
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const star = page.getByRole("radio", { name: "1 star", exact: true });
  await star.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("radio", { name: "2 stars" })).toBeChecked();
  await expect(page.locator(".feedback-stars label")).toHaveText(["★", "★", "☆", "☆", "☆"]);
  await expect(page.locator(".feedback-stars input").first()).toHaveCSS("opacity", "0");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Logout", exact: true }).click();
  await page.getByRole("button", { name: "Skip and log out" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
