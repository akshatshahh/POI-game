import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import type { Poi, GpsPoint } from "../lib/types";
import { api } from "../lib/api";
import "leaflet/dist/leaflet.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.css";
import "react-leaflet-cluster/dist/assets/MarkerCluster.Default.css";

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

// Smaller blue pin for background/nearby POIs
const NEARBY_ICON = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [17, 28],
  iconAnchor: [8, 28],
  popupAnchor: [1, -24],
  shadowSize: [28, 28],
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
  const [allNearby, setAllNearby] = useState<Poi[]>([]);

  const candidateIds = new Set(candidates.map((c) => c.id));

  useEffect(() => {
    let cancelled = false;
    api
      .get<Poi[]>(`/pois/nearby?lat=${gpsPoint.lat}&lon=${gpsPoint.lon}&radius=500&limit=50`)
      .then((pois) => { if (!cancelled) setAllNearby(pois); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [gpsPoint.lat, gpsPoint.lon]);

  return (
    <MapContainer center={center} zoom={19} className="game-map">
      <MapUpdater lat={gpsPoint.lat} lon={gpsPoint.lon} onMapReady={onMapReady} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Background nearby POIs — smaller pins, no clustering */}
      {allNearby
        .filter((p) => !candidateIds.has(p.id))
        .map((poi) => (
          <Marker key={`bg-${poi.id}`} position={[poi.lat, poi.lon]} icon={NEARBY_ICON}>
            <Popup>
              <strong>{poi.name}</strong>
              <br />
              <span style={{ color: "#64748b", fontSize: "0.8em" }}>{poi.category}</span>
            </Popup>
          </Marker>
        ))}

      {/* GPS location — red pin, no clustering */}
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

      {/* Candidate POIs — clustered with spiderfy so overlapping pins fan out on click */}
      <MarkerClusterGroup
        chunkedLoading
        spiderfyOnMaxZoom
        showCoverageOnHover={false}
        maxClusterRadius={40}
        zoomToBoundsOnClick={false}
        spiderfyDistanceMultiplier={1.5}
      >
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
      </MarkerClusterGroup>
    </MapContainer>
  );
}
