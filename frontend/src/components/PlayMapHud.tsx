import type { AnswerResponse, GpsPoint, Poi } from "../lib/types";
import { formatCategory } from "../lib/formatCategory";

interface PlayMapHudProps {
  gpsPoint: GpsPoint;
  candidates: Poi[];
  selectedPoiIds: Set<string>;
  priorAnswers?: number;
  answered: boolean;
  feedback: AnswerResponse | null;
  submitting: boolean;
  secondsRemaining: number;
  currentScore: number;
  error: string | null;
  onSelectPoi: (poiId: string) => void;
  onSubmit: () => void;
  onNextQuestion: () => void;
  onRecenter: () => void;
}

export function PlayMapHud({
  gpsPoint,
  candidates,
  selectedPoiIds,
  priorAnswers = 0,
  answered,
  feedback,
  submitting,
  secondsRemaining,
  currentScore,
  error,
  onSelectPoi,
  onSubmit,
  onNextQuestion,
  onRecenter,
}: PlayMapHudProps) {
  const hasTime = Boolean(gpsPoint.weekday || gpsPoint.local_time);
  const visitTime = [gpsPoint.weekday, gpsPoint.local_time].filter(Boolean).join(" · ");
  const selectedPois = candidates.filter((candidate) => selectedPoiIds.has(candidate.id));
  const selectionCount = selectedPoiIds.size;
  const selectedNames = selectedPois.map((poi) => poi.name).join(", ");
  const countdown = `${Math.floor(secondsRemaining / 60)}:${String(secondsRemaining % 60).padStart(2, "0")}`;
  const timerUrgent = secondsRemaining <= 10;
  const denseChoices = candidates.length > 8;

  return (
    <div className="play-hud">
      <section
        className={`play-hud-panel${denseChoices ? " play-hud-panel--dense" : ""}`}
        aria-label="Question HUD"
      >
        <header className="hud-header">
          <p className="hud-prompt">Which POIs was this person most likely visiting?</p>
          <button
            type="button"
            className="hud-recenter-button"
            onClick={onRecenter}
            title="Recenter map on all locations"
            aria-label="Recenter map on all locations"
          >
            <span className="hud-recenter-icon" aria-hidden="true">⊕</span>
            <span className="hud-recenter-label">Recenter</span>
          </button>
        </header>

        <div className="hud-meta-row">
          {hasTime && (
            <div className="hud-meta-item hud-meta-item--visit" data-tutorial="visit-time">
              <span className="hud-meta-label">Visit</span>
              <strong>{visitTime}</strong>
            </div>
          )}
          {!answered && (
            <div
              className={`hud-meta-item hud-question-timer${timerUrgent ? " hud-question-timer--urgent" : ""}`}
              role="timer"
              aria-label={`${secondsRemaining} seconds remaining`}
            >
              <span className="hud-meta-label">Time left</span>
              <strong className="hud-question-timer-value">{countdown}</strong>
            </div>
          )}
          <div className="hud-meta-item hud-score" aria-label={`Current score: ${currentScore} points`}>
            <span className="hud-meta-label">Score</span>
            <strong>{currentScore} pts</strong>
          </div>
          {priorAnswers > 0 && (
            <div
              className="hud-meta-item hud-prior"
              title={
                priorAnswers === 1
                  ? "1 other person has answered this question"
                  : `${priorAnswers} other people have answered this question`
              }
            >
              <span className="hud-meta-label">Answered</span>
              <strong>{priorAnswers} other{priorAnswers === 1 ? "" : "s"}</strong>
            </div>
          )}
        </div>

        {!answered && candidates.length > 0 && (
          <ul
            className={`hud-candidate-grid${denseChoices ? " hud-candidate-grid--dense" : ""}`}
            aria-label="Candidate places"
            data-tutorial="poi-choices"
          >
            {candidates.map((poi, index) => {
              const num = index + 1;
              const isSelected = selectedPoiIds.has(poi.id);
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
                    {isSelected && <span className="hud-candidate-check" aria-hidden="true">✓</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {!answered ? (
          <div className="hud-action-area">
            <div className="hud-selection" aria-live="polite">
              {selectionCount > 0 ? (
                <>
                  <span className="hud-selection-label">Selected ({selectionCount})</span>
                  <span className="hud-selection-name" title={selectedNames}>{selectedNames}</span>
                </>
              ) : (
                <span className="hud-selection-placeholder">Select one or more POIs</span>
              )}
            </div>
            {error && <p className="hud-error">{error}</p>}
            <button
              type="button"
              onClick={onSubmit}
              disabled={selectionCount === 0 || submitting}
              className="btn btn-primary hud-submit"
              data-tutorial="submit-answer"
            >
              {submitting
                ? "Submitting…"
                : `Submit Answer${selectionCount > 1 ? "s" : ""}`}
            </button>
          </div>
        ) : (
          <div className="hud-result-area">
            {feedback && (
              <div className="hud-feedback">
                <div className="hud-feedback-score">+{feedback.score_awarded} points</div>
                <p className="hud-feedback-hint">
                  +10 bonus if other players confirm your picks when this question finalizes!
                </p>
                {feedback.selected_poi_ids.length > 0 && (
                  <p className="hud-feedback-poi">
                    You picked: <strong>
                      {feedback.selected_poi_ids
                        .map((id) => candidates.find((candidate) => candidate.id === id)?.name ?? id)
                        .join(", ")}
                    </strong>
                  </p>
                )}
              </div>
            )}
            {error && <p className="hud-error">{error}</p>}
            <button type="button" onClick={onNextQuestion} className="btn btn-primary hud-submit">
              Next Question →
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
