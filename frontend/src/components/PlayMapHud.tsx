import { useEffect, useRef } from "react";
import type { AnswerResponse, GpsPoint, Poi } from "../lib/types";
import { formatCategory } from "../lib/formatCategory";

interface PlayMapHudProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiId: string | null;
  answered: boolean;
  feedback: AnswerResponse | null;
  submitting: boolean;
  error: string | null;
  onSelectPoi: (poiId: string) => void;
  onSubmit: () => void;
  onNextQuestion: () => void;
  onRecenter: () => void;
}

export function PlayMapHud({
  gpsPoint,
  candidates,
  selectedPoiId,
  answered,
  feedback,
  submitting,
  error,
  onSelectPoi,
  onSubmit,
  onNextQuestion,
  onRecenter,
}: PlayMapHudProps) {
  const listRef = useRef<HTMLUListElement>(null);
  const hasTime = gpsPoint.weekday || gpsPoint.local_date || gpsPoint.local_time;
  const selectedPoi = candidates.find((c) => c.id === selectedPoiId) ?? null;
  const selectedNum = selectedPoiId
    ? candidates.findIndex((c) => c.id === selectedPoiId) + 1
    : 0;

  useEffect(() => {
    if (!selectedPoiId || answered) return;
    const row = listRef.current?.querySelector<HTMLElement>(
      `[data-poi-id="${CSS.escape(selectedPoiId)}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedPoiId, answered]);

  return (
    <div className="play-hud">
      <div className="play-hud-top">
        <button type="button" className="hud-top-row" onClick={onRecenter} aria-label="Recenter map on the visit location">
          {hasTime && (
            <span className="hud-visit-chip" title="Visit date/time">
              <span className="hud-visit-label">Visit date/time</span>
              <span className="hud-visit-values">
                {gpsPoint.weekday && <strong>{gpsPoint.weekday}</strong>}
                {gpsPoint.local_date && <span className="hud-visit-date">{gpsPoint.local_date}</span>}
                {gpsPoint.local_time && <span className="hud-visit-time">{gpsPoint.local_time}</span>}
              </span>
            </span>
          )}
          <span className="hud-prompt">Which POI was this person most likely visiting?</span>
          <span className="hud-recenter" title="Recenter map">
            <span className="hud-recenter-icon" aria-hidden="true">⊕</span>
            <span className="hud-recenter-text">Recenter map</span>
          </span>
        </button>
      </div>

      <div className="play-hud-bottom">
        {!answered && candidates.length > 0 && (
          <ul ref={listRef} className="hud-candidate-list" aria-label="Candidate places">
            {candidates.map((poi, index) => {
              const num = index + 1;
              const isSelected = poi.id === selectedPoiId;
              return (
                <li key={poi.id} data-poi-id={poi.id}>
                  <button
                    type="button"
                    className={`hud-candidate-row${isSelected ? " hud-candidate-row--selected" : ""}`}
                    onClick={() => onSelectPoi(poi.id)}
                    aria-pressed={isSelected}
                  >
                    <span className="hud-candidate-num" aria-hidden="true">{num}</span>
                    <span className="hud-candidate-text">
                      <span className="hud-candidate-name">{poi.name}</span>
                      <span className="hud-candidate-cat">{formatCategory(poi.category)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {!answered ? (
          <>
            {selectedPoi && (
              <div className="hud-selection">
                <span className="hud-selection-label">Selected:</span>
                <span className="hud-selection-num" aria-hidden="true">{selectedNum}</span>
                <span className="hud-selection-name">{selectedPoi.name}</span>
                <span className="hud-selection-cat">{formatCategory(selectedPoi.category)}</span>
              </div>
            )}
            {error && <p className="hud-error">{error}</p>}
            <button
              onClick={onSubmit}
              disabled={!selectedPoiId || submitting}
              className="btn btn-primary btn-lg hud-submit"
            >
              {submitting ? "Submitting…" : "Submit Answer"}
            </button>
          </>
        ) : (
          <>
            {feedback && (
              <div className="hud-feedback">
                <div className="hud-feedback-score">+{feedback.score_awarded} points</div>
                <p className="hud-feedback-hint">
                  Consensus bonus (+10) unlocks when others agree!
                </p>
                {selectedPoi && (
                  <p className="hud-feedback-poi">
                    You picked: <strong>{selectedPoi.name}</strong>
                  </p>
                )}
              </div>
            )}
            {error && <p className="hud-error">{error}</p>}
            <button onClick={onNextQuestion} className="btn btn-primary btn-lg hud-submit">
              Next Question →
            </button>
          </>
        )}
      </div>
    </div>
  );
}
