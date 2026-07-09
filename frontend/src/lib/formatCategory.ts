/** Format Overture-style category slugs for display: "thai_restaurant" → "Thai restaurant". */
export function formatCategory(category: string | null | undefined): string {
  if (!category) return "";
  const cleaned = category.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  if (!cleaned) return "";
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}
