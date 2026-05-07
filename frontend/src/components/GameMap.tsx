import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import type { Poi, GpsPoint } from "../lib/types";
import type { TimeOfDay } from "../lib/timeOfDay";
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

const POI_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const SELECTED_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});


interface GameMapProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiId: string | null;
  onSelectPoi: (poiId: string) => void;
  answered?: boolean;
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
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 20 });
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
        map.flyToBounds(L.latLngBounds(points), { padding: [50, 50], maxZoom: 20, duration: 0.6 });
      } else {
        map.flyTo([lat, lon], 19, { duration: 0.6 });
      }
    });
  }, [map, lat, lon, candidates, onMapReady]);

  return null;
}

export function GameMap({ gpsPoint, candidates, selectedPoiId, onSelectPoi, answered = false, onMapReady, timeOfDay = "day" }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];

  return (
    <MapContainer center={center} zoom={19} maxZoom={21} className={`game-map game-map--${timeOfDay}`}>
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} candidates={candidates} onMapReady={onMapReady} />
      <TileLayer
        key={timeOfDay}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url={TILE_URLS[timeOfDay]}
        maxNativeZoom={19}
        maxZoom={21}
      />

      {/* GPS location — red pin, no popup so not selectable as an answer */}
      <Marker position={center} icon={GPS_ICON} />

      {/* Candidate POIs — render unselected first, selected last so it's on top */}
      {candidates
        .slice()
        .sort((a, b) => (a.id === selectedPoiId ? 1 : 0) - (b.id === selectedPoiId ? 1 : 0))
        .map((poi) => {
          const isSelected = poi.id === selectedPoiId;
          return (
            <Marker
              key={poi.id}
              position={[poi.lat, poi.lon]}
              icon={isSelected ? SELECTED_ICON : POI_ICON}
              zIndexOffset={isSelected ? 1000 : 0}
              ref={(ref) => { if (ref) ref.setZIndexOffset(isSelected ? 1000 : 0); }}
              eventHandlers={{ click: () => onSelectPoi(poi.id) }}
            >
              <Tooltip permanent direction="top" offset={[0, -42]} className={isSelected ? "poi-tooltip poi-tooltip--selected" : "poi-tooltip"}>
                <strong>{poi.name}</strong>
                <span className="poi-tooltip-cat">{poi.category}</span>
                {answered && <span className="poi-tooltip-dist">{poi.distance_meters.toFixed(0)}m</span>}
              </Tooltip>
            </Marker>
          );
        })}
    </MapContainer>
  );
}
