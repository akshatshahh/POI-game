import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { GameMap } from "../components/GameMap";
import { PlayMapHud } from "../components/PlayMapHud";
import { FirstTimeTutorial } from "../components/FirstTimeTutorial";
import { LoadingScreen } from "../components/LoadingScreen";
import { api, isApiError } from "../lib/api";
import { timeOfDay } from "../lib/timeOfDay";
import type { AnswerResponse, Question } from "../lib/types";

const QUESTION_TIME_LIMIT_SECONDS = 60;
const QUESTION_TIME_LIMIT_MS = QUESTION_TIME_LIMIT_SECONDS * 1000;

interface PlayProps {
  userId: string;
  currentScore: number;
  isFirstTimePlayer: boolean;
  onScoreUpdate: () => void;
}

export function Play({ userId, currentScore, isFirstTimePlayer, onScoreUpdate }: PlayProps) {
  const navigate = useNavigate();
  const [question, setQuestion] = useState<Question | null>(null);
  const [selectedPoiIds, setSelectedPoiIds] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<AnswerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [secondsRemaining, setSecondsRemaining] = useState(QUESTION_TIME_LIMIT_SECONDS);
  const [tutorialOpen, setTutorialOpen] = useState(isFirstTimePlayer);
  const recenterRef = useRef<() => void>(() => {});
  const timerDeadlineRef = useRef<number | null>(null);
  const timerRemainingMsRef = useRef(QUESTION_TIME_LIMIT_MS);
  const timedOutQuestionRef = useRef<string | null>(null);
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

  const fetchQuestion = useCallback(async (excludeQuestionId?: string) => {
    setLoading(true);
    setSelectedPoiIds(new Set());
    setFeedback(null);
    setError(null);
    try {
      const query = excludeQuestionId
        ? `?exclude_question_id=${encodeURIComponent(excludeQuestionId)}`
        : "";
      const q = await api.get<Question>(`/game/next-question${query}`);
      timerDeadlineRef.current = null;
      timerRemainingMsRef.current = QUESTION_TIME_LIMIT_MS;
      timedOutQuestionRef.current = null;
      setSecondsRemaining(QUESTION_TIME_LIMIT_SECONDS);
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

  const handleTimeExpired = useCallback(() => {
    if (!question || timedOutQuestionRef.current === question.question_id) return;
    timedOutQuestionRef.current = question.question_id;
    void fetchQuestion(question.question_id);
  }, [fetchQuestion, question]);

  useEffect(() => {
    const timerActive =
      question !== null &&
      !loading &&
      !submitting &&
      !feedback &&
      !tutorialOpen;

    if (!timerActive || !question) {
      if (timerDeadlineRef.current !== null) {
        timerRemainingMsRef.current = Math.max(
          0,
          timerDeadlineRef.current - Date.now(),
        );
        timerDeadlineRef.current = null;
      }
      return;
    }

    if (timedOutQuestionRef.current === question.question_id) return;

    timerDeadlineRef.current = Date.now() + timerRemainingMsRef.current;

    const updateTimer = () => {
      if (timerDeadlineRef.current === null) return;
      const remainingMs = Math.max(0, timerDeadlineRef.current - Date.now());
      timerRemainingMsRef.current = remainingMs;
      setSecondsRemaining(Math.ceil(remainingMs / 1000));

      if (remainingMs === 0) {
        timerDeadlineRef.current = null;
        handleTimeExpired();
      }
    };

    updateTimer();
    const interval = window.setInterval(updateTimer, 250);

    return () => {
      window.clearInterval(interval);
      if (timerDeadlineRef.current !== null) {
        timerRemainingMsRef.current = Math.max(
          0,
          timerDeadlineRef.current - Date.now(),
        );
        timerDeadlineRef.current = null;
      }
    };
  }, [feedback, handleTimeExpired, loading, question, submitting, tutorialOpen]);

  const handleSubmit = async () => {
    if (
      !question ||
      selectedPoiIds.size === 0 ||
      secondsRemaining === 0 ||
      timedOutQuestionRef.current === question.question_id
    ) return;
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
          <button onClick={() => void fetchQuestion()} className="btn btn-primary">
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
        secondsRemaining={secondsRemaining}
        currentScore={currentScore}
        error={error}
        onSelectPoi={togglePoi}
        onSubmit={handleSubmit}
        onNextQuestion={fetchQuestion}
        onRecenter={() => recenterRef.current?.()}
      />
      {isFirstTimePlayer && userId && (
        <FirstTimeTutorial
          userId={userId}
          onVisibilityChange={setTutorialOpen}
        />
      )}
    </div>
  );
}
