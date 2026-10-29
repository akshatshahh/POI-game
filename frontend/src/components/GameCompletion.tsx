import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { api } from "../lib/api";

interface GameCompletionProps {
  defaultEmail: string;
  finalScore: number;
}

interface CampaignSubscriptionResponse {
  id: string;
  email: string;
  created_at: string;
}

interface CampaignSubscriptionStatus {
  subscribed: boolean;
  email: string | null;
  created_at: string | null;
}

type ConfettiStyle = CSSProperties & {
  "--confetti-drift": string;
  "--confetti-spin": string;
};

const CONFETTI_COLORS = ["#fbbf24", "#22c55e", "#38bdf8", "#f472b6", "#fb7185"];
const CONFETTI_PIECES = Array.from({ length: 36 }, (_, index) => ({
  left: `${(index * 37) % 100}%`,
  delay: `${(index % 9) * 0.07}s`,
  duration: `${2.2 + (index % 6) * 0.16}s`,
  drift: `${((index * 29) % 140) - 70}px`,
  spin: `${360 + (index % 5) * 180}deg`,
  color: CONFETTI_COLORS[index % CONFETTI_COLORS.length],
}));

export function GameCompletion({ defaultEmail, finalScore }: GameCompletionProps) {
  const [subscribedEmail, setSubscribedEmail] = useState("");
  const [checkingSubscription, setCheckingSubscription] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const titleRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  useEffect(() => {
    let active = true;
    void api.get<CampaignSubscriptionStatus>("/campaign-subscriptions/me")
      .then((result) => {
        if (active && result.subscribed && result.email) {
          setSubscribedEmail(result.email);
        }
      })
      .catch(() => {
        if (active) {
          setError("We could not check your notification preference. You can still subscribe.");
        }
      })
      .finally(() => {
        if (active) setCheckingSubscription(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function subscribe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;

    setSaving(true);
    setError("");
    setNotice("");
    try {
      const result = await api.post<CampaignSubscriptionResponse>(
        "/campaign-subscriptions",
        { email: defaultEmail },
      );
      setSubscribedEmail(result.email);
    } catch (err) {
      setError(err instanceof Error ? err.message : "We could not save your email. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  async function unsubscribe() {
    if (saving) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await api.delete("/campaign-subscriptions/me");
      setSubscribedEmail("");
      setNotice("Campaign notifications have been removed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "We could not remove notifications. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="game-complete" aria-labelledby="game-complete-title">
      <div className="completion-confetti" aria-hidden="true">
        {CONFETTI_PIECES.map((piece, index) => (
          <span
            key={index}
            className="completion-confetti-piece"
            style={{
              left: piece.left,
              backgroundColor: piece.color,
              animationDelay: piece.delay,
              animationDuration: piece.duration,
              "--confetti-drift": piece.drift,
              "--confetti-spin": piece.spin,
            } as ConfettiStyle}
          />
        ))}
      </div>

      <div className="game-complete-content">
        <p className="game-complete-eyebrow">Campaign complete</p>
        <h1 id="game-complete-title" ref={titleRef} tabIndex={-1}>Congratulations!</h1>
        <p className="game-complete-message">
          You answered every available question. Thank you for helping improve
          our understanding of real-world visits.
        </p>
        <p className="game-complete-score">
          Total score <strong>{finalScore}</strong> points
        </p>

        <div className="campaign-notification-box">
          {checkingSubscription ? (
            <p className="campaign-notification-checking" role="status">
              Checking your notification preference...
            </p>
          ) : subscribedEmail ? (
            <div className="campaign-notification-success">
              <h2>You are on the list</h2>
              <p role="status">
                We will notify <strong>{subscribedEmail}</strong> when the next
                campaign goes live.
              </p>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => void unsubscribe()}
                disabled={saving}
              >
                {saving ? "Removing..." : "Remove notification"}
              </button>
              {error && <p className="campaign-notification-error" role="alert">{error}</p>}
            </div>
          ) : (
            <form onSubmit={subscribe}>
              <h2>Play the next campaign</h2>
              <p>Enter your email to be notified when the next campaign goes live.</p>
              <label htmlFor="campaign-email">Email address</label>
              <div className="campaign-notification-controls">
                <input
                  id="campaign-email"
                  name="email"
                  type="email"
                  value={defaultEmail}
                  autoComplete="email"
                  maxLength={320}
                  readOnly
                  required
                />
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? "Saving..." : "Notify me"}
                </button>
              </div>
              <p className="campaign-notification-privacy">
                This is your account email. We will only use it for campaign
                announcements, and you can remove the notification at any time.
              </p>
              {notice && <p className="campaign-notification-notice" role="status">{notice}</p>}
              {error && <p className="campaign-notification-error" role="alert">{error}</p>}
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
