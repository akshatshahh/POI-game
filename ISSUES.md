# Open Issues

Running list of UX, product, and engineering issues to revisit later.

---

## UX-1: Overlapping POI pins at high zoom

**Status:** Open
**Priority:** Medium
**Reported:** May 7, 2026

### Problem
When the GPS point falls in a high-density area, multiple candidate POI pins
end up stacked at nearly the same coordinate. Even at maximum zoom (21), the
permanent labels overlap each other and the pins are hard to distinguish.

### Possible solutions (from brainstorm)

1. **Numbered pins + bottom sheet list** (recommended) — Apple/Google Maps
   style. Each candidate gets a numbered badge; a bottom sheet/panel shows the
   same numbered list with names, categories, and distances. Tap row or pin to
   select.
2. **Spiderfy on click** — overlapping pins cluster into a single bubble that
   fans out radially with connector lines when clicked.
3. **Cluster groups** — numbered cluster bubbles replace overlapping pins;
   zoom-in expands them. Better for many pins.
4. **Carousel synced with map** — horizontal swipeable cards at the bottom; map
   auto-pans to highlight matching pin.
5. **Smart label de-collision** — auto-place labels in free space with thin
   leader lines back to pins (libraries: maplibre-gl, leaflet-labelgun).

### Notes
- Mockups generated and saved under `assets/option-*.png`.
- Mobile-first preference: option 1 is the best fit for game UX.
