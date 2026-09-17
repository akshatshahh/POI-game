import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import type { Poi, GpsPoint } from "../lib/types";
import type { TimeOfDay } from "../lib/timeOfDay";
import { formatCategory } from "../lib/formatCategory";
import "leaflet/dist/leaflet.css";

const CARTO_API_KEY = import.meta.env.VITE_CARTO_API_KEY?.trim();

function cartoTileUrl(style: string): string {
  const url = `https://{s}.basemaps.cartocdn.com/${style}/{z}/{x}/{y}{r}.png`;
  return CARTO_API_KEY ? `${url}?key=${encodeURIComponent(CARTO_API_KEY)}` : url;
}

const TILE_URLS: Record<TimeOfDay, string> = {
  day: cartoTileUrl("rastertiles/voyager_labels_under"),
  evening: cartoTileUrl("rastertiles/voyager_labels_under"),
  night: cartoTileUrl("rastertiles/dark_all"),
};

const GPS_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  className: "gps-location-marker",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Extra bottom padding keeps the HUD from covering markers.
const FIT_OPTIONS: L.FitBoundsOptions = {
  paddingTopLeft: [50, 50],
  paddingBottomRight: [50, 220],
  maxZoom: 20,
};

/** Bounds covering the GPS point and all candidate POIs; null when there are no candidates. */
function questionBounds(lat: number, lon: number, candidates: Poi[]): L.LatLngBounds | null {
  if (candidates.length === 0) return null;
  const points: L.LatLngExpression[] = [
    [lat, lon],
    ...candidates.map((c) => [c.lat, c.lon] as L.LatLngExpression),
  ];
  return L.latLngBounds(points);
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function numberedPoiIcon(
  num: number,
  selected: boolean,
  dimmed: boolean,
  name?: string,
  category?: string,
): L.DivIcon {
  const badgeSize = selected ? 40 : 30;
  const classes = [
    "poi-num-marker",
    selected ? "poi-num-marker--selected" : "",
    dimmed ? "poi-num-marker--dimmed" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const labelHtml =
    selected && name
      ? `<span class="poi-num-label">
           <strong>${num}. ${escapeHtml(name)}</strong>
           ${category ? `<span class="poi-num-label-cat">${escapeHtml(category)}</span>` : ""}
         </span>`
      : "";

  // Selected: badge + name label to the RIGHT (avoids colliding with GPS label above the red pin)
  const html = selected
    ? `<div class="poi-num-wrap poi-num-wrap--selected"><span class="poi-num-badge">${num}</span>${labelHtml}</div>`
    : `<div class="poi-num-wrap"><span class="poi-num-badge">${num}</span></div>`;

  const iconW = selected ? 240 : badgeSize;
  const iconH = selected ? 48 : badgeSize;

  return L.divIcon({
    className: classes,
    html,
    iconSize: [iconW, iconH],
    // Anchor on the badge center (left side of the wide selected icon)
    iconAnchor: [badgeSize / 2, iconH / 2],
  });
}

interface GameMapProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiIds: Set<string>;
  onSelectPoi: (poiId: string) => void;
  onMapReady?: (recenter: () => void) => void;
  timeOfDay?: TimeOfDay;
}

function MapUpdater({ lat, lon, candidates, onMapReady }: {
  lat: number;
  lon: number;
  candidates: Poi[];
  onMapReady?: (fn: () => void) => void;
}) {
  const map = useMap();

  useEffect(() => {
    const bounds = questionBounds(lat, lon, candidates);
    if (bounds) {
      map.fitBounds(bounds, FIT_OPTIONS);
    } else {
      map.setView([lat, lon], 19);
    }
  }, [map, lat, lon, candidates]);

  useEffect(() => {
    onMapReady?.(() => {
      const bounds = questionBounds(lat, lon, candidates);
      if (bounds) {
        map.flyToBounds(bounds, { ...FIT_OPTIONS, duration: 0.6 });
      } else {
        map.flyTo([lat, lon], 19, { duration: 0.6 });
      }
    });
  }, [map, lat, lon, candidates, onMapReady]);

  return null;
}

function SelectionFocuser({
  selectedPoiIds,
  candidates,
}: {
  selectedPoiIds: Set<string>;
  candidates: Poi[];
}) {
  const map = useMap();
  const prevSizeRef = useRef(0);

  useEffect(() => {
    if (selectedPoiIds.size === 0) {
      prevSizeRef.current = 0;
      return;
    }
    // Only fly when a new POI is added (not removed)
    if (selectedPoiIds.size <= prevSizeRef.current) {
      prevSizeRef.current = selectedPoiIds.size;
      return;
    }
    prevSizeRef.current = selectedPoiIds.size;
    const lastId = Array.from(selectedPoiIds).pop();
    const poi = candidates.find((c) => c.id === lastId);
    if (!poi) return;
    const targetZoom = Math.max(map.getZoom(), 18);
    map.flyTo([poi.lat, poi.lon], Math.min(targetZoom, 20), {
      duration: 0.55,
      easeLinearity: 0.25,
    });
  }, [map, selectedPoiIds, candidates]);

  return null;
}

export function GameMap({ gpsPoint, candidates, selectedPoiIds, onSelectPoi, onMapReady, timeOfDay = "day" }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];
  const hasSelection = selectedPoiIds.size > 0;

  const numbered = useMemo(
    () =>
      candidates
        .map((poi, index) => ({ poi, num: index + 1 }))
        .sort((a, b) => (selectedPoiIds.has(a.poi.id) ? 1 : 0) - (selectedPoiIds.has(b.poi.id) ? 1 : 0)),
    [candidates, selectedPoiIds],
  );

  return (
    <MapContainer center={center} zoom={19} maxZoom={21} className={`game-map game-map--${timeOfDay}`}>
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} candidates={candidates} onMapReady={onMapReady} />
      <SelectionFocuser selectedPoiIds={selectedPoiIds} candidates={candidates} />
      <TileLayer
        key={timeOfDay}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url={TILE_URLS[timeOfDay]}
        maxNativeZoom={19}
        maxZoom={21}
      />

      <Marker position={center} icon={GPS_ICON} interactive={false} zIndexOffset={500}>
        <Tooltip permanent direction="left" offset={[-8, -16]} className="gps-tooltip">
          Actual visit location
        </Tooltip>
      </Marker>

      {numbered.map(({ poi, num }) => {
        const isSelected = selectedPoiIds.has(poi.id);
        const dimmed = hasSelection && !isSelected;
        const category = formatCategory(poi.category);
        return (
          <Marker
            key={poi.id}
            position={[poi.lat, poi.lon]}
            icon={numberedPoiIcon(num, isSelected, dimmed, poi.name, category)}
            zIndexOffset={isSelected ? 2000 : dimmed ? -100 : num}
            riseOnHover
            eventHandlers={{
              click: (e) => {
                L.DomEvent.stopPropagation(e.originalEvent);
                onSelectPoi(poi.id);
              },
            }}
          >
            {!isSelected && (
              <Tooltip direction="top" offset={[0, -18]} className="poi-tooltip" opacity={1}>
                <strong>{poi.name}</strong>
                <span className="poi-tooltip-cat">{category}</span>
              </Tooltip>
            )}
          </Marker>
        );
      })}
    </MapContainer>
  );
}
