import { useEffect, useRef } from "react";
import type { User } from "../lib/types";
import { UserAvatar } from "./UserAvatar";

interface UserProfileProps {
  user: User;
  onClose: () => void;
}

function joinedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

export function UserProfile({ user, onClose }: UserProfileProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const displayName = user.display_name || "POI Game player";

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      opener?.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className="user-profile-dialog"
      aria-labelledby="user-profile-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="user-profile-content">
        <header className="user-profile-header">
          <UserAvatar
            name={displayName}
            url={user.avatar_url}
            className="user-profile-avatar"
            fallbackClassName="user-profile-avatar--fallback"
          />
          <div>
            <p className="user-profile-eyebrow">Your POI Game profile</p>
            <h2 id="user-profile-title">{displayName}</h2>
            <p className="user-profile-handle">
              {user.username ? `@${user.username}` : "Username not set"}
            </p>
          </div>
          <button type="button" className="user-profile-close" onClick={onClose}>
            Close
          </button>
        </header>

        <section className="user-profile-stats" aria-label="Game activity">
          <div>
            <strong>{user.score ?? 0}</strong>
            <span>Points</span>
          </div>
          <div>
            <strong>{user.answers_count ?? 0}</strong>
            <span>Questions answered</span>
          </div>
        </section>

        <dl className="user-profile-details">
          <div>
            <dt>Name</dt>
            <dd>{displayName}</dd>
          </div>
          <div>
            <dt>Username</dt>
            <dd>{user.username || "Not set"}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{user.email || "Not available"}</dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>
              <time dateTime={user.created_at}>{joinedDate(user.created_at)}</time>
            </dd>
          </div>
          <div>
            <dt>Account type</dt>
            <dd>{user.is_admin ? "Administrator" : "Player"}</dd>
          </div>
        </dl>

        <footer className="user-profile-footer">
          <p>These details come from your POI Game account.</p>
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </footer>
      </div>
    </dialog>
  );
}
