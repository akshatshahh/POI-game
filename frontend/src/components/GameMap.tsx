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

function MapUpdater({ lat, lon, onMapReady }: { lat: number; lon: number; onMapReady?: (fn: () => void) => void }) {
  const map = useMap();

  useEffect(() => {
    map.setView([lat, lon], 19);
  }, [map, lat, lon]);

  useEffect(() => {
    onMapReady?.(() => map.flyTo([lat, lon], 19, { duration: 0.6 }));
  }, [map, lat, lon, onMapReady]);

  return null;
}

export function GameMap({ gpsPoint, candidates, selectedPoiId, onSelectPoi, answered = false, onMapReady }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];

  return (
    <MapContainer center={center} zoom={19} className="game-map">
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} onMapReady={onMapReady} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* GPS location — red pin, not clickable */}
      <Marker position={center} icon={GPS_ICON} interactive={false} />

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
