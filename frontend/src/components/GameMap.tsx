import { useEffect, useMemo } from "react";
import { MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import type { GpsPoint, Poi } from "../lib/types";
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

const MAP_EDGE_PADDING = 52;
const HUD_GAP = 18;
const MARKER_CLEARANCE = 24;

interface MapPadding {
  topLeft: L.Point;
  bottomRight: L.Point;
}

function questionBounds(lat: number, lon: number, candidates: Poi[]): L.LatLngBounds | null {
  if (candidates.length === 0) return null;
  const points: L.LatLngExpression[] = [
    [lat, lon],
    ...candidates.map((candidate) => [candidate.lat, candidate.lon] as L.LatLngExpression),
  ];
  return L.latLngBounds(points);
}

function mapPadding(map: L.Map): MapPadding {
  const container = map.getContainer();
  const mapRect = container.getBoundingClientRect();
  const hud = container
    .closest(".play-map-stack")
    ?.querySelector<HTMLElement>(".play-hud-panel");

  let bottom = MAP_EDGE_PADDING;
  if (hud) {
    const hudRect = hud.getBoundingClientRect();
    const overlapsMap =
      hudRect.left < mapRect.right &&
      hudRect.right > mapRect.left &&
      hudRect.top < mapRect.bottom &&
      hudRect.bottom > mapRect.top;

    if (overlapsMap) {
      bottom = Math.max(
        bottom,
        Math.ceil(mapRect.bottom - hudRect.top + HUD_GAP + MARKER_CLEARANCE),
      );
    }
  }

  const maximumBottom = Math.max(
    MAP_EDGE_PADDING,
    Math.floor(mapRect.height - MAP_EDGE_PADDING - 120),
  );

  return {
    topLeft: L.point(MAP_EDGE_PADDING, MAP_EDGE_PADDING),
    bottomRight: L.point(MAP_EDGE_PADDING, Math.min(bottom, maximumBottom)),
  };
}

function fitLocations(
  map: L.Map,
  lat: number,
  lon: number,
  candidates: Poi[],
  animate = false,
): void {
  const bounds = questionBounds(lat, lon, candidates);
  const padding = mapPadding(map);

  if (bounds) {
    map.fitBounds(bounds, {
      paddingTopLeft: padding.topLeft,
      paddingBottomRight: padding.bottomRight,
      maxZoom: 20,
      animate,
      duration: animate ? 0.45 : undefined,
    });
    return;
  }

  map.setView([lat, lon], 19, { animate });
}

function panFocusClearOfHud(
  map: L.Map,
  lat: number,
  lon: number,
  candidates: Poi[],
  selectedPoiIds: Set<string>,
): void {
  const padding = mapPadding(map);
  const size = map.getSize();
  const safe = {
    left: padding.topLeft.x,
    top: padding.topLeft.y,
    right: size.x - padding.bottomRight.x,
    bottom: size.y - padding.bottomRight.y,
  };
  const gpsLocation: L.LatLngExpression = [lat, lon];
  const allLocations: L.LatLngExpression[] = [
    gpsLocation,
    ...candidates.map((candidate) => [candidate.lat, candidate.lon] as L.LatLngExpression),
  ];
  const selectedLocations: L.LatLngExpression[] = [
    gpsLocation,
    ...candidates
      .filter((candidate) => selectedPoiIds.has(candidate.id))
      .map((candidate) => [candidate.lat, candidate.lon] as L.LatLngExpression),
  ];

  const projectedBounds = (locations: L.LatLngExpression[]) => {
    const points = locations.map((location) => map.latLngToContainerPoint(location));
    return {
      minX: Math.min(...points.map((point) => point.x)),
      minY: Math.min(...points.map((point) => point.y)),
      maxX: Math.max(...points.map((point) => point.x)),
      maxY: Math.max(...points.map((point) => point.y)),
    };
  };
  const fitsSafeArea = (projected: ReturnType<typeof projectedBounds>) =>
    projected.maxX - projected.minX <= safe.right - safe.left &&
    projected.maxY - projected.minY <= safe.bottom - safe.top;

  const allProjected = projectedBounds(allLocations);
  let focusLocations = fitsSafeArea(allProjected)
    ? allLocations
    : selectedPoiIds.size > 0
      ? selectedLocations
      : [gpsLocation];
  let projected = projectedBounds(focusLocations);

  if (!fitsSafeArea(projected) && selectedPoiIds.size > 0) {
    map.fitBounds(L.latLngBounds(focusLocations), {
      paddingTopLeft: padding.topLeft,
      paddingBottomRight: padding.bottomRight,
      maxZoom: map.getZoom(),
      animate: true,
      duration: 0.25,
    });
    return;
  }

  if (!fitsSafeArea(projected)) {
    focusLocations = [gpsLocation];
    projected = projectedBounds(focusLocations);
  }

  let panX = 0;
  let panY = 0;
  if (projected.minX < safe.left) panX = projected.minX - safe.left;
  else if (projected.maxX > safe.right) panX = projected.maxX - safe.right;
  if (projected.minY < safe.top) panY = projected.minY - safe.top;
  else if (projected.maxY > safe.bottom) panY = projected.maxY - safe.bottom;

  if (Math.abs(panX) > 1 || Math.abs(panY) > 1) {
    map.panBy([panX, panY], { animate: true, duration: 0.2 });
  }
}

function numberedPoiIcon(num: number, selected: boolean): L.DivIcon {
  const badgeSize = selected ? 40 : 30;
  const classes = ["poi-num-marker", selected ? "poi-num-marker--selected" : ""]
    .filter(Boolean)
    .join(" ");

  return L.divIcon({
    className: classes,
    html: `<div class="poi-num-wrap"><span class="poi-num-badge">${num}</span></div>`,
    iconSize: [badgeSize, badgeSize],
    iconAnchor: [badgeSize / 2, badgeSize / 2],
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

function MapUpdater({
  lat,
  lon,
  candidates,
  selectedPoiIds,
  onMapReady,
}: {
  lat: number;
  lon: number;
  candidates: Poi[];
  selectedPoiIds: Set<string>;
  onMapReady?: (fn: () => void) => void;
}) {
  const map = useMap();

  useEffect(() => {
    let frame = 0;
    const fitAllLocations = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        map.invalidateSize({ animate: false, pan: false });
        fitLocations(map, lat, lon, candidates);
      });
    };

    fitAllLocations();
    const resizeObserver = new ResizeObserver(fitAllLocations);
    resizeObserver.observe(map.getContainer());
    const hud = map
      .getContainer()
      .closest(".play-map-stack")
      ?.querySelector<HTMLElement>(".play-hud-panel");
    if (hud) resizeObserver.observe(hud);

    return () => {
      window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
    };
  }, [map, lat, lon, candidates]);

  useEffect(() => {
    const keepFocusVisible = () => {
      panFocusClearOfHud(map, lat, lon, candidates, selectedPoiIds);
    };
    const frame = window.requestAnimationFrame(keepFocusVisible);
    map.on("zoomend", keepFocusVisible);

    return () => {
      window.cancelAnimationFrame(frame);
      map.off("zoomend", keepFocusVisible);
    };
  }, [map, lat, lon, candidates, selectedPoiIds]);

  useEffect(() => {
    onMapReady?.(() => {
      fitLocations(map, lat, lon, candidates, true);
    });
  }, [map, lat, lon, candidates, onMapReady]);

  return null;
}

export function GameMap({
  gpsPoint,
  candidates,
  selectedPoiIds,
  onSelectPoi,
  onMapReady,
  timeOfDay = "day",
}: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];
  const numbered = useMemo(
    () =>
      candidates
        .map((poi, index) => ({ poi, num: index + 1 }))
        .sort(
          (a, b) =>
            Number(selectedPoiIds.has(a.poi.id)) - Number(selectedPoiIds.has(b.poi.id)),
        ),
    [candidates, selectedPoiIds],
  );

  return (
    <MapContainer center={center} zoom={19} maxZoom={21} className={`game-map game-map--${timeOfDay}`}>
      <MapUpdater
        lat={gpsPoint.lat}
        lon={gpsPoint.lon}
        candidates={candidates}
        selectedPoiIds={selectedPoiIds}
        onMapReady={onMapReady}
      />
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
        const category = formatCategory(poi.category);
        return (
          <Marker
            key={poi.id}
            position={[poi.lat, poi.lon]}
            icon={numberedPoiIcon(num, isSelected)}
            zIndexOffset={isSelected ? 2000 : num}
            riseOnHover
            eventHandlers={{
              click: (event) => {
                L.DomEvent.stopPropagation(event.originalEvent);
                onSelectPoi(poi.id);
              },
            }}
          >
            <Tooltip direction="top" offset={[0, -18]} className="poi-tooltip" opacity={1}>
              <strong>{poi.name}</strong>
              <span className="poi-tooltip-cat">{category}</span>
            </Tooltip>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
