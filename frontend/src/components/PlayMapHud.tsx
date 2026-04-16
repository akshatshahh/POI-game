import type { AnswerResponse, GpsPoint, Poi } from "../lib/types";

interface PlayMapHudProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiId: string | null;
  answered: boolean;
  feedback: AnswerResponse | null;
  submitting: boolean;
  error: string | null;
  onSubmit: () => void;
  onNextQuestion: () => void;
}

export function PlayMapHud({
  gpsPoint,
  candidates,
  selectedPoiId,
  answered,
  feedback,
  submitting,
  error,
  onSubmit,
  onNextQuestion,
}: PlayMapHudProps) {
  const hasTime = gpsPoint.weekday || gpsPoint.local_date || gpsPoint.local_time;
  const selectedPoi = candidates.find((c) => c.id === selectedPoiId) ?? null;

  return (
    <div className="play-hud">
      {/* Top overlay: single compact row */}
      <div className="play-hud-top">
        <div className="hud-top-row">
          {hasTime && (
            <span className="hud-visit-chip">
              {gpsPoint.weekday && <>{gpsPoint.weekday}</>}
              {gpsPoint.local_date && <>, {gpsPoint.local_date}</>}
              {gpsPoint.local_time && <> · {gpsPoint.local_time}</>}
            </span>
          )}
          <span className="hud-prompt">Which POI was this person most likely visiting?</span>
        </div>
      </div>

      {/* Bottom overlay: selection + submit / feedback */}
      <div className="play-hud-bottom">
        {!answered ? (
          <>
            {selectedPoi && (
              <div className="hud-selection">
                <span className="hud-selection-label">Selected:</span>
                <span className="hud-selection-name">{selectedPoi.name}</span>
                <span className="hud-selection-cat">{selectedPoi.category}</span>
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
                    {" — "}
                    {selectedPoi.distance_meters.toFixed(0)}m away
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
