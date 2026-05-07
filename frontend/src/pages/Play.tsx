import { useCallback, useEffect, useRef, useState } from "react";
import { GameMap } from "../components/GameMap";
import { PlayMapHud } from "../components/PlayMapHud";
import { ClockPanel } from "../components/ClockPanel";
import { api } from "../lib/api";
import { timeOfDay } from "../lib/timeOfDay";
import type { AnswerResponse, Question } from "../lib/types";

interface PlayProps {
  onScoreUpdate: () => void;
}

export function Play({ onScoreUpdate }: PlayProps) {
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedPoiId, setSelectedPoiId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const recenterRef = useRef<() => void>(() => {});
  const handleMapReady = useCallback((fn: () => void) => { recenterRef.current = fn; }, []);

  const fetchQuestion = useCallback(async () => {
    setLoading(true);
    setSelectedPoiId(null);
    setFeedback(null);
    setError(null);
    try {
      const q = await api.get<Question>("/game/next-question");
      setQuestion(q);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load question";
      if (msg.includes("404")) {
        setError("No more questions available. Check back later!");
      } else {
        setError(msg);
      }
      setQuestion(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  const handleSubmit = async () => {
    if (!question || !selectedPoiId) return;
    setSubmitting(true);
    try {
      const result = await api.post<AnswerResponse>("/game/answer", {
        question_id: question.question_id,
        selected_poi_id: selectedPoiId,
      });
      setFeedback(result);
      onScoreUpdate();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="play-map-stack play-map-stack--loading">
        <div className="loading-screen">
          <div className="spinner" />
          <p>Loading question…</p>
        </div>
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
        selectedPoiId={selectedPoiId}
        onSelectPoi={setSelectedPoiId}
        answered={!!feedback}
        onMapReady={handleMapReady}
        timeOfDay={tod}
      />
      <PlayMapHud
        gpsPoint={question.gps_point}
        candidates={question.candidates}
        selectedPoiId={selectedPoiId}
        answered={!!feedback}
        feedback={feedback}
        submitting={submitting}
        error={error}
        onSubmit={handleSubmit}
        onNextQuestion={fetchQuestion}
        onRecenter={() => recenterRef.current?.()}
      />
      <ClockPanel gpsPoint={question.gps_point} />
    </div>
  );
}
