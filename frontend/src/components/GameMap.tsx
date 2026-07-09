import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import type { Poi, GpsPoint } from "../lib/types";
import type { TimeOfDay } from "../lib/timeOfDay";
import { formatCategory } from "../lib/formatCategory";
import "leaflet/dist/leaflet.css";

const TILE_URLS: Record<TimeOfDay, string> = {
  day: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png",
  evening: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}{r}.png",
  night: "https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png",
};

const GPS_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const FIT_PADDING_TL: L.PointExpression = [50, 50];
const FIT_PADDING_BR: L.PointExpression = [50, 220];

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

  const html = `<div class="poi-num-wrap">${labelHtml}<span class="poi-num-badge">${num}</span></div>`;
  const iconW = selected ? 220 : badgeSize;
  const iconH = selected ? 78 : badgeSize;
  const anchorX = selected ? iconW / 2 : badgeSize / 2;
  const anchorY = selected ? iconH - badgeSize / 2 : badgeSize / 2;

  return L.divIcon({
    className: classes,
    html,
    iconSize: [iconW, iconH],
    iconAnchor: [anchorX, anchorY],
  });
}

interface GameMapProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiId: string | null;
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
    if (candidates.length > 0) {
      const points: L.LatLngExpression[] = [
        [lat, lon],
        ...candidates.map((c) => [c.lat, c.lon] as L.LatLngExpression),
      ];
      map.fitBounds(L.latLngBounds(points), {
        paddingTopLeft: FIT_PADDING_TL,
        paddingBottomRight: FIT_PADDING_BR,
        maxZoom: 20,
      });
    } else {
      map.setView([lat, lon], 19);
    }
  }, [map, lat, lon, candidates]);

  useEffect(() => {
    onMapReady?.(() => {
      if (candidates.length > 0) {
        const points: L.LatLngExpression[] = [
          [lat, lon],
          ...candidates.map((c) => [c.lat, c.lon] as L.LatLngExpression),
        ];
        map.flyToBounds(L.latLngBounds(points), {
          paddingTopLeft: FIT_PADDING_TL,
          paddingBottomRight: FIT_PADDING_BR,
          maxZoom: 20,
          duration: 0.6,
        });
      } else {
        map.flyTo([lat, lon], 19, { duration: 0.6 });
      }
    });
  }, [map, lat, lon, candidates, onMapReady]);

  return null;
}

function SelectionFocuser({
  selectedPoiId,
  candidates,
}: {
  selectedPoiId: string | null;
  candidates: Poi[];
}) {
  const map = useMap();

  useEffect(() => {
    if (!selectedPoiId) return;
    const poi = candidates.find((c) => c.id === selectedPoiId);
    if (!poi) return;
    const targetZoom = Math.max(map.getZoom(), 18);
    map.flyTo([poi.lat, poi.lon], Math.min(targetZoom, 20), {
      duration: 0.55,
      easeLinearity: 0.25,
    });
  }, [map, selectedPoiId, candidates]);

  return null;
}

export function GameMap({ gpsPoint, candidates, selectedPoiId, onSelectPoi, onMapReady, timeOfDay = "day" }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];
  const hasSelection = !!selectedPoiId;

  const numbered = useMemo(
    () =>
      candidates
        .map((poi, index) => ({ poi, num: index + 1 }))
        .sort((a, b) => (a.poi.id === selectedPoiId ? 1 : 0) - (b.poi.id === selectedPoiId ? 1 : 0)),
    [candidates, selectedPoiId],
  );

  return (
    <MapContainer center={center} zoom={19} maxZoom={21} className={`game-map game-map--${timeOfDay}`}>
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} candidates={candidates} onMapReady={onMapReady} />
      <SelectionFocuser selectedPoiId={selectedPoiId} candidates={candidates} />
      <TileLayer
        key={timeOfDay}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url={TILE_URLS[timeOfDay]}
        maxNativeZoom={19}
        maxZoom={21}
      />

      <Marker position={center} icon={GPS_ICON} interactive={false} zIndexOffset={500}>
        <Tooltip permanent direction="top" offset={[0, -42]} className="gps-tooltip">
          Actual visit location
        </Tooltip>
      </Marker>

      {numbered.map(({ poi, num }) => {
        const isSelected = poi.id === selectedPoiId;
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
            ref={(ref) => {
              if (!ref) return;
              ref.setZIndexOffset(isSelected ? 2000 : dimmed ? -100 : num);
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
