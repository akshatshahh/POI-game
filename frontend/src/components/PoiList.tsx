import type { GpsPoint, Poi } from "../lib/types";

interface PoiListProps {
  candidates: Poi[];
  selectedPoiId: string | null;
  onSelectPoi: (poiId: string) => void;
  gpsPoint: GpsPoint;
}

export function PoiList({ candidates, selectedPoiId, onSelectPoi, gpsPoint }: PoiListProps) {
  const hasTime = gpsPoint.weekday || gpsPoint.local_date || gpsPoint.local_time;

  return (
    <div className="poi-list">
      {hasTime && (
        <div className="visit-time-banner">
          <span className="visit-time-label">Visit recorded</span>
          <span className="visit-time-value">
            {gpsPoint.weekday}{gpsPoint.local_date ? `, ${gpsPoint.local_date}` : ""}
            {gpsPoint.local_time ? ` at ${gpsPoint.local_time}` : ""}
          </span>
        </div>
      )}
      <h3>Nearby Places</h3>
      <p className="poi-list-hint">Which POI was this person most likely visiting?</p>
      <div className="poi-items">
        {candidates.map((poi) => (
          <button
            key={poi.id}
            className={`poi-item ${poi.id === selectedPoiId ? "poi-item--selected" : ""}`}
            onClick={() => onSelectPoi(poi.id)}
          >
            <div className="poi-item-main">
              <span className="poi-name">{poi.name}</span>
              <span className="poi-category">{poi.category}</span>
            </div>
            <span className="poi-distance">{poi.distance_meters.toFixed(0)}m</span>
          </button>
        ))}
      </div>
    </div>
  );
}
