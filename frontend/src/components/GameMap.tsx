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
}

function MapUpdater({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 17);
  }, [map, center]);
  return null;
}

export function GameMap({ gpsPoint, candidates, selectedPoiId, onSelectPoi, answered = false }: GameMapProps) {
  const center: [number, number] = [gpsPoint.lat, gpsPoint.lon];

  return (
    <MapContainer center={center} zoom={17} className="game-map">
      <MapUpdater center={center} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Marker position={center} icon={GPS_ICON}>
        <Popup>
          <strong>GPS Point</strong>
          <br />
          {gpsPoint.lat.toFixed(6)}, {gpsPoint.lon.toFixed(6)}
          {gpsPoint.timestamp && (
            <>
              <br />
              {new Date(gpsPoint.timestamp).toLocaleString()}
            </>
          )}
        </Popup>
      </Marker>
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
