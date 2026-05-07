export type TimeOfDay = "day" | "evening" | "night";

/**
 * Classify a local time string (e.g. "7:32 AM" or "21:15") into a coarse
 * time-of-day tier so we can theme the map and overlays accordingly.
 *   day     06:00 – 16:59  (bright, light theme)
 *   evening 17:00 – 19:59  (dusk, mid-tone theme)
 *   night   20:00 – 05:59  (dark theme)
 */
export function timeOfDay(time: string | null | undefined): TimeOfDay {
  if (!time) return "day";
  const match = time.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
  if (!match) return "day";
  let hours = parseInt(match[1], 10);
  const period = match[3]?.toUpperCase();
  if (period === "PM" && hours < 12) hours += 12;
  if (period === "AM" && hours === 12) hours = 0;
  if (hours >= 6 && hours < 17) return "day";
  if (hours >= 17 && hours < 20) return "evening";
  return "night";
}
