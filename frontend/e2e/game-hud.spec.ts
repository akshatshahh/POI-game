import { expect, test, type Locator, type Page } from "@playwright/test";

const user = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "hud-check",
  email: "hud-check@example.com",
  display_name: "HUD Check",
  avatar_url: null,
  score: 245,
  answers_count: 4,
  is_admin: false,
  created_at: "2026-09-23T12:00:00Z",
};

const candidates = Array.from({ length: 8 }, (_, index) => ({
  id: `poi-${index + 1}`,
  name: index === 7 ? "A Place With a Longer Display Name" : `Nearby Place ${index + 1}`,
  category: index % 2 === 0 ? "restaurant" : "retail_store",
  lat: 34.0204 + index * 0.00003,
  lon: -118.2857 + index * 0.00003,
}));

const question = {
  question_id: "00000000-0000-4000-8000-000000000201",
  gps_point: {
    lat: 34.02065,
    lon: -118.28543,
    timestamp: "2026-09-23T19:30:00Z",
    weekday: "Wednesday",
    local_date: "2026-09-23",
    local_time: "12:30 PM",
  },
  candidates,
  prior_answers: 2,
};

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
    if (pathname === "/game/next-question") {
      await route.fulfill({ status: 200, headers, json: question });
      return;
    }

    await route.fulfill({ status: 404, headers, json: { detail: "Not found" } });
  });
}

async function expectInsideViewport(page: Page, locator: Locator): Promise<void> {
  const viewport = page.viewportSize();
  const box = await locator.boundingBox();

  expect(viewport).not.toBeNull();
  expect(box).not.toBeNull();
  if (!viewport || !box) return;

  expect(box.x).toBeGreaterThanOrEqual(0);
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1);
}

test("keeps eight POIs in a compact HUD without covering map locations", async ({ page }) => {
  await mockApi(page);
  await page.goto("/play");

  const hud = page.getByRole("region", { name: "Question HUD" });
  const choices = page.locator(".hud-candidate-grid > li");

  await expect(hud).toBeVisible();
  await expect(hud.getByText("Which POIs was this person most likely visiting?")).toBeVisible();
  await expect(hud.getByText("Wednesday · 12:30 PM")).toBeVisible();
  await expect(hud.getByRole("timer")).toContainText("1:00");
  await expect(hud.getByText("245 pts")).toBeVisible();
  await expect(choices).toHaveCount(8);
  await expect(page.locator(".clock-panel")).toHaveCount(0);
  await expect(page.locator(".navbar .user-score")).toHaveCount(0);

  const hudSizing = await hud.evaluate((element) => {
    const prompt = element.querySelector<HTMLElement>(".hud-prompt");
    const candidateName = element.querySelector<HTMLElement>(".hud-candidate-name");
    if (!prompt || !candidateName) return null;
    return {
      panelWidth: element.getBoundingClientRect().width,
      promptFontSize: Number.parseFloat(getComputedStyle(prompt).fontSize),
      candidateFontSize: Number.parseFloat(getComputedStyle(candidateName).fontSize),
    };
  });
  expect(hudSizing).not.toBeNull();
  if (hudSizing) {
    expect(hudSizing.promptFontSize).toBeGreaterThanOrEqual(14);
    expect(hudSizing.candidateFontSize).toBeGreaterThanOrEqual(13);
    if ((page.viewportSize()?.width ?? 0) > 1040) {
      expect(hudSizing.panelWidth).toBeGreaterThanOrEqual(1030);
    }
  }

  const layout = await choices.evaluateAll((items) =>
    items.map((item) => {
      const rect = item.getBoundingClientRect();
      return { x: Math.round(rect.x), y: Math.round(rect.y) };
    }),
  );
  expect(new Set(layout.map(({ x }) => x)).size).toBe(2);
  expect(new Set(layout.map(({ y }) => y)).size).toBe(4);

  const gridOverflow = await page.locator(".hud-candidate-grid").evaluate((element) => {
    const style = window.getComputedStyle(element);
    return {
      overflowY: style.overflowY,
      fits: element.scrollHeight <= element.clientHeight + 1,
    };
  });
  expect(gridOverflow.overflowY).toBe("visible");
  expect(gridOverflow.fits).toBe(true);

  await expectInsideViewport(page, hud);
  for (let index = 0; index < 8; index += 1) {
    await expectInsideViewport(page, choices.nth(index));
  }

  const markers = page.locator(".poi-num-marker");
  await expect(markers).toHaveCount(8);
  await markers.first().click();
  await expect(page.locator(".poi-num-marker--selected")).toHaveCount(1);
  await page.getByRole("button", { name: /Nearby Place 2/ }).click();
  await expect(page.locator(".poi-num-marker--selected")).toHaveCount(2);
  await expect(hud.getByText("Selected (2)")).toBeVisible();
  await expect(hud.getByRole("button", { name: "Submit Answers" })).toBeEnabled();
  const locationsClearHud = async () =>
    page.evaluate(() => {
        const map = document.querySelector<HTMLElement>(".game-map");
        const panel = document.querySelector<HTMLElement>(".play-hud-panel");
        const locations = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".gps-location-marker, .gps-tooltip, .poi-num-marker",
          ),
        );
        if (!map || !panel || locations.length < 10) return false;

        const mapRect = map.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();
        return locations.every((location) => {
          const rect = location.getBoundingClientRect();
          const overlapsPanel =
            rect.left < panelRect.right &&
            rect.right > panelRect.left &&
            rect.top < panelRect.bottom &&
            rect.bottom > panelRect.top;
          return (
            rect.left >= mapRect.left - 1 &&
            rect.top >= mapRect.top - 1 &&
            rect.right <= mapRect.right + 1 &&
            rect.bottom <= mapRect.bottom + 1 &&
            !overlapsPanel
          );
        });
      });

  await expect.poll(locationsClearHud).toBe(true);

  await page.locator(".leaflet-control-zoom-in").click();
  await expect.poll(locationsClearHud).toBe(true);

  await page.locator(".leaflet-control-zoom-out").click();
  await page.locator(".leaflet-control-zoom-out").click();
  await expect.poll(locationsClearHud).toBe(true);
});
