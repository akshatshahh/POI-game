export type TimeOfDay = "day" | "evening" | "night";

/**
 * Parse a local time string from the backend (e.g. "7:32 AM" or "21:15")
 * into 24-hour hours/minutes. Returns null when the string is missing or
 * doesn't match. Shared by the map theming below and the ClockPanel.
 */
export function parseLocalTime(
  time: string | null | undefined,
): { hours: number; minutes: number } | null {
  if (!time) return null;
  const match = time.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
  if (!match) return null;
  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const period = match[3]?.toUpperCase();
  if (period === "PM" && hours < 12) hours += 12;
  if (period === "AM" && hours === 12) hours = 0;
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  return { hours, minutes };
}

/**
 * Classify a local time string into a coarse time-of-day tier so we can
 * theme the map and overlays accordingly.
 *   day     06:00 – 16:59  (bright, light theme)
 *   evening 17:00 – 19:59  (dusk, mid-tone theme)
 *   night   20:00 – 05:59  (dark theme)
 */
export function timeOfDay(time: string | null | undefined): TimeOfDay {
  const parsed = parseLocalTime(time);
  if (!parsed) return "day";
  if (parsed.hours >= 6 && parsed.hours < 17) return "day";
  if (parsed.hours >= 17 && parsed.hours < 20) return "evening";
  return "night";
}
