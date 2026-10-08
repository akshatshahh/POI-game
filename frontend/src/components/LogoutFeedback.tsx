import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../lib/api";

interface Props {
  mode: "logout" | "feedback";
  onComplete: () => Promise<void>;
  onCancel: () => void;
}

export function LogoutFeedback({ mode, onComplete, onCancel }: Props) {
  const isLogout = mode === "logout";
  const dialog = useRef<HTMLDialogElement>(null);
  const submitting = useRef(false);
  const leaving = useRef(false);
  const active = useRef(false);
  const pendingRequest = useRef<AbortController | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    active.current = true;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      active.current = false;
      pendingRequest.current?.abort();
      element?.close();
      opener?.focus();
    };
  }, []);

  function cancel() {
    if (isLogout && (submitting.current || leaving.current)) return;
    active.current = false;
    pendingRequest.current?.abort();
    onCancel();
  }

  async function leave() {
    if (leaving.current) return;
    leaving.current = true;
    await onComplete();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || leaving.current) return;
    const values = new FormData(event.currentTarget);
    submitting.current = true;
    setSaving(true);
    setError("");
    const controller = new AbortController();
    pendingRequest.current = controller;
    try {
      await api.post("/feedback", {
        rating: Number(values.get("rating")),
        comments: String(values.get("comments") || "").trim() || null,
        email: String(values.get("email") || "").trim() || null,
      }, { signal: controller.signal });
    } catch {
      if (active.current && !leaving.current) {
        setError(isLogout ? "Your feedback could not be saved. Please try again, or skip and log out." : "Your feedback could not be saved. Please try again, or close the form.");
        setSaving(false);
      }
      submitting.current = false;
      return;
    }
    if (!active.current) return;
    await leave();
  }

  return (
    <dialog ref={dialog} className="logout-feedback" aria-labelledby="feedback-title" onCancel={(event) => {
      event.preventDefault();
      cancel();
    }}>
      <form onSubmit={submit}>
        <h2 id="feedback-title">{isLogout ? "Before you go" : "Share your feedback"}</h2>
        <p>How was your experience? Feedback is optional.</p>
        <fieldset className="feedback-stars" aria-describedby="feedback-scale">
          <legend>Rate your experience (1–5 stars)</legend>
          {[1, 2, 3, 4, 5].map((rating) => (
            <label key={rating}>
              <input type="radio" name="rating" value={rating} required aria-label={`${rating} ${rating === 1 ? "star" : "stars"}`} />
              <span aria-hidden="true">★</span>
            </label>
          ))}
        </fieldset>
        <p id="feedback-scale">1 = least liked · 5 = best</p>
        <label htmlFor="feedback-comments">Comments (optional)</label>
        <textarea id="feedback-comments" name="comments" maxLength={4000} rows={4}
          placeholder="You can write any feedback or questions, tell us what you could not understand on the page, or report any errors."
          aria-description="Share feedback, questions, anything unclear on the page, or errors you encountered." />
        <label htmlFor="feedback-email">Email (optional)</label>
        <input id="feedback-email" name="email" type="email" maxLength={320} autoComplete="email" />
        <p>Only project administrators can read this feedback. Email is only needed if you want a reply. Feedback is not included in research-label exports.</p>
        {error && <p role="alert">{error}</p>}
        <div className="feedback-actions">
          <button className="feedback-button feedback-button--primary" type="submit" disabled={saving}>{saving ? "Saving…" : isLogout ? "Submit feedback and log out" : "Submit feedback"}</button>
          {isLogout ? <>
            <button className="feedback-button feedback-button--secondary" type="button" onClick={() => void leave()}>Skip and log out</button>
            <button className="feedback-button feedback-button--quiet" type="button" disabled={saving} onClick={cancel}>Keep playing</button>
          </> : <button className="feedback-button feedback-button--secondary" type="button" onClick={cancel}>Close</button>}
        </div>
      </form>
    </dialog>
  );
}
