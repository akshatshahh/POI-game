import { useCallback, useEffect, useRef, useState } from "react";
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
  error,
  onSelectPoi,
  onSubmit,
  onNextQuestion,
  onRecenter,
}: PlayMapHudProps) {
  const listRef = useRef<HTMLUListElement>(null);
  const [scrollMetrics, setScrollMetrics] = useState({
    scrollable: false,
    thumbTop: 0,
    thumbHeight: 0,
  });
  const hasTime = !!(gpsPoint.weekday || gpsPoint.local_time);
  const selectedPois = candidates.filter((c) => selectedPoiIds.has(c.id));
  const selectionCount = selectedPoiIds.size;

  const updateScrollbar = useCallback(() => {
    const el = listRef.current;
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    const scrollable = scrollHeight > clientHeight + 1;
    if (!scrollable) {
      setScrollMetrics({ scrollable: false, thumbTop: 0, thumbHeight: 0 });
      return;
    }
    const thumbHeight = Math.max(28, (clientHeight / scrollHeight) * clientHeight);
    const maxTop = clientHeight - thumbHeight;
    const thumbTop =
      scrollHeight === clientHeight
        ? 0
        : (scrollTop / (scrollHeight - clientHeight)) * maxTop;
    setScrollMetrics({ scrollable: true, thumbTop, thumbHeight });
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const frame = window.requestAnimationFrame(updateScrollbar);
    el.addEventListener("scroll", updateScrollbar, { passive: true });
    const ro = new ResizeObserver(updateScrollbar);
    ro.observe(el);
    return () => {
      window.cancelAnimationFrame(frame);
      el.removeEventListener("scroll", updateScrollbar);
      ro.disconnect();
    };
  }, [answered, candidates, updateScrollbar]);

  useEffect(() => {
    if (selectedPoiIds.size === 0 || answered) return;
    const lastId = Array.from(selectedPoiIds).pop();
    if (!lastId) return;
    const row = listRef.current?.querySelector<HTMLElement>(
      `[data-poi-id="${CSS.escape(lastId)}"]`,
    );
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selectedPoiIds, answered]);

  return (
    <div className="play-hud">
      <div className="play-hud-top">
        <div className="hud-top-cluster">
          <button type="button" className="hud-top-row" onClick={onRecenter} aria-label="Recenter map on the visit location">
            {hasTime && (
              <span className="hud-visit-chip" title="Visit day/time">
                <span className="hud-visit-label">Visit day/time</span>
                <span className="hud-visit-values">
                  {gpsPoint.weekday && <strong>{gpsPoint.weekday}</strong>}
                  {gpsPoint.local_time && <span className="hud-visit-time">{gpsPoint.local_time}</span>}
                </span>
              </span>
            )}
            <span className="hud-prompt">Which POI(s) was this person most likely visiting?</span>
            <span className="hud-recenter" title="Recenter map">
              <span className="hud-recenter-icon" aria-hidden="true">⊕</span>
              <span className="hud-recenter-text">Recenter map</span>
            </span>
          </button>
          {priorAnswers > 0 && (
            <div
              className="hud-prior-badge"
              title={
                priorAnswers === 1
                  ? "1 other person has answered this question"
                  : `${priorAnswers} other people have answered this question`
              }
            >
              <span className="hud-prior-count">{priorAnswers}</span>
              <span className="hud-prior-label">
                {priorAnswers === 1 ? "other answered" : "others answered"}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="play-hud-bottom">
        {!answered && candidates.length > 0 && (
          <div className="hud-candidate-scroll" data-tutorial="poi-choices">
            <ul ref={listRef} className="hud-candidate-list" aria-label="Candidate places">
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
                      <span className="hud-candidate-check" aria-hidden="true">{isSelected ? "✓" : ""}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {scrollMetrics.scrollable && (
              <div className="hud-candidate-scrollbar" aria-hidden="true">
                <div
                  className="hud-candidate-scrollbar-thumb"
                  style={{
                    height: `${scrollMetrics.thumbHeight}px`,
                    transform: `translateY(${scrollMetrics.thumbTop}px)`,
                  }}
                />
              </div>
            )}
          </div>
        )}

        {!answered ? (
          <>
            {selectedPois.length > 0 && (
              <div className="hud-selection">
                <span className="hud-selection-label">
                  Selected ({selectionCount}):
                </span>
                {selectedPois.map((poi) => {
                  const num = candidates.findIndex((c) => c.id === poi.id) + 1;
                  return (
                    <span key={poi.id} className="hud-selection-item">
                      <span className="hud-selection-num" aria-hidden="true">{num}</span>
                      <span className="hud-selection-name">{poi.name}</span>
                    </span>
                  );
                })}
              </div>
            )}
            {error && <p className="hud-error">{error}</p>}
            <button
              onClick={onSubmit}
              disabled={selectionCount === 0 || submitting}
              className="btn btn-primary btn-lg hud-submit"
              data-tutorial="submit-answer"
            >
              {submitting ? "Submitting…" : `Submit Answer${selectionCount > 1 ? "s" : ""}`}
            </button>
          </>
        ) : (
          <>
            {feedback && (
              <div className="hud-feedback">
                <div className="hud-feedback-score">+{feedback.score_awarded} points</div>
                <p className="hud-feedback-hint">
                  +10 bonus if other players confirm your pick when this
                  question finalizes!
                </p>
                {feedback.selected_poi_ids && feedback.selected_poi_ids.length > 0 && (
                  <p className="hud-feedback-poi">
                    You picked: <strong>
                      {feedback.selected_poi_ids
                        .map((id) => candidates.find((c) => c.id === id)?.name ?? id)
                        .join(", ")}
                    </strong>
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
