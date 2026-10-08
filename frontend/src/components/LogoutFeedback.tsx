import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../lib/api";

interface Props {
  onLogout: () => Promise<void>;
  onCancel: () => void;
}

export function LogoutFeedback({ onLogout, onCancel }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const submitting = useRef(false);
  const leaving = useRef(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);

  async function leave() {
    if (leaving.current) return;
    leaving.current = true;
    await onLogout();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || leaving.current) return;
    const values = new FormData(event.currentTarget);
    submitting.current = true;
    setSaving(true);
    setError("");
    try {
      await api.post("/feedback", {
        rating: Number(values.get("rating")),
        comments: String(values.get("comments") || "").trim() || null,
        email: String(values.get("email") || "").trim() || null,
      });
    } catch {
      if (!leaving.current) {
        setError("Your feedback could not be saved. Please try again, or skip and log out.");
        setSaving(false);
      }
      submitting.current = false;
      return;
    }
    await leave();
  }

  return (
    <dialog ref={dialog} className="logout-feedback" aria-labelledby="feedback-title" onCancel={(event) => {
      if (saving) event.preventDefault();
      else onCancel();
    }}>
      <form onSubmit={submit}>
        <h2 id="feedback-title">Before you go</h2>
        <p>How was your experience? Feedback is optional.</p>
        <fieldset className="feedback-stars">
          <legend>Rate your experience (1–5 stars)</legend>
          {[1, 2, 3, 4, 5].map((rating) => (
            <label key={rating}>
              <input type="radio" name="rating" value={rating} required aria-label={`${rating} ${rating === 1 ? "star" : "stars"}`} />
              <span aria-hidden="true">★</span><span>{rating}</span>
            </label>
          ))}
        </fieldset>
        <label htmlFor="feedback-comments">Comments (optional)</label>
        <p id="feedback-help">You can write any feedback or questions, tell us what you could not understand on the page, or report any errors.</p>
        <textarea id="feedback-comments" name="comments" maxLength={4000} rows={4} aria-describedby="feedback-help" />
        <label htmlFor="feedback-email">Email (optional)</label>
        <input id="feedback-email" name="email" type="email" maxLength={320} autoComplete="email" />
        <p>Only project administrators can read this feedback. Email is only needed if you want a reply. Feedback is not included in research-label exports.</p>
        {error && <p role="alert">{error}</p>}
        <div className="feedback-actions">
          <button type="submit" disabled={saving}>{saving ? "Saving…" : "Submit feedback and log out"}</button>
          <button type="button" onClick={() => void leave()}>Skip and log out</button>
          <button type="button" disabled={saving} onClick={onCancel}>Keep playing</button>
        </div>
      </form>
    </dialog>
  );
}
