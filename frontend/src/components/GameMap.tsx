import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { Poi, GpsPoint } from "../lib/types";
import "leaflet/dist/leaflet.css";

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

export function GameMap({ gpsPoint, candidates, selectedPoiId, onSelectPoi, answered = false, onMapReady }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];

  return (
    <MapContainer center={center} zoom={19} maxZoom={21} className="game-map">
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} candidates={candidates} onMapReady={onMapReady} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png"
        maxNativeZoom={19}
        maxZoom={21}
      />

      {/* GPS location — red pin, no popup so not selectable as an answer */}
      <Marker position={center} icon={GPS_ICON} />

      {/* Candidate POIs */}
      {candidates.map((poi) => (
        <Marker
          key={poi.id}
          position={[poi.lat, poi.lon]}
          icon={poi.id === selectedPoiId ? SELECTED_ICON : POI_ICON}
          eventHandlers={{ click: () => onSelectPoi(poi.id) }}
        >
          <Popup>
            <strong>{poi.name}</strong>
            <br />
            {poi.category}{answered ? ` — ${poi.distance_meters.toFixed(0)}m` : ""}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
