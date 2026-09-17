import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GameMap } from "../components/GameMap";
import { PlayMapHud } from "../components/PlayMapHud";
import { ClockPanel } from "../components/ClockPanel";
import { FirstTimeTutorial } from "../components/FirstTimeTutorial";
import { LoadingScreen } from "../components/LoadingScreen";
import { api, isApiError } from "../lib/api";
import { timeOfDay } from "../lib/timeOfDay";
import type { AnswerResponse, Question } from "../lib/types";

interface PlayProps {
  userId: string;
  isFirstTimePlayer: boolean;
  onScoreUpdate: () => void;
}

export function Play({ userId, isFirstTimePlayer, onScoreUpdate }: PlayProps) {
  const navigate = useNavigate();
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedPoiIds, setSelectedPoiIds] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const recenterRef = useRef<() => void>(() => {});
  const handleMapReady = useCallback((fn: () => void) => { recenterRef.current = fn; }, []);

  const togglePoi = useCallback((poiId: string) => {
    setSelectedPoiIds((prev) => {
      const next = new Set(prev);
      if (next.has(poiId)) {
        next.delete(poiId);
      } else {
        next.add(poiId);
      }
      return next;
    });
  }, []);

  const fetchQuestion = useCallback(async () => {
    setLoading(true);
    setSelectedPoiIds(new Set());
    setFeedback(null);
    setError(null);
    try {
      const q = await api.get<Question>("/game/next-question");
      setQuestion(q);
    } catch (err) {
      if (isApiError(err, 401)) {
        navigate("/", { replace: true });
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to load question");
      setQuestion(null);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  const handleSubmit = async () => {
    if (!question || selectedPoiIds.size === 0) return;
    setSubmitting(true);
    try {
      const result = await api.post<AnswerResponse>("/game/answer", {
        question_id: question.question_id,
        selected_poi_ids: Array.from(selectedPoiIds),
      });
      setFeedback(result);
      onScoreUpdate();
    } catch (err) {
      if (isApiError(err, 401)) {
        navigate("/", { replace: true });
        return;
      }
      if (isApiError(err, 409)) {
        await fetchQuestion();
        return;
      }
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="play-map-stack play-map-stack--loading">
        <LoadingScreen label="Loading question…" />
      </div>
    );
  }

  if (error && !question) {
    return (
      <div className="play-map-stack play-map-stack--loading">
        <div className="game-empty">
          <h2>No Questions Available</h2>
          <p>{error}</p>
          <button onClick={fetchQuestion} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!question) return null;

  const tod = timeOfDay(question.gps_point.local_time);

  return (
    <div className={`play-map-stack play-map-stack--${tod}`} data-tod={tod}>
      <GameMap
        gpsPoint={question.gps_point}
        candidates={question.candidates}
        selectedPoiIds={selectedPoiIds}
        onSelectPoi={togglePoi}
        onMapReady={handleMapReady}
        timeOfDay={tod}
      />
      <PlayMapHud
        gpsPoint={question.gps_point}
        candidates={question.candidates}
        selectedPoiIds={selectedPoiIds}
        priorAnswers={question.prior_answers ?? 0}
        answered={!!feedback}
        feedback={feedback}
        submitting={submitting}
        error={error}
        onSelectPoi={togglePoi}
        onSubmit={handleSubmit}
        onNextQuestion={fetchQuestion}
        onRecenter={() => recenterRef.current?.()}
      />
      <ClockPanel gpsPoint={question.gps_point} />
      {isFirstTimePlayer && userId && <FirstTimeTutorial userId={userId} />}
    </div>
  );
}
