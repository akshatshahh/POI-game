import { Link } from "react-router-dom";
import type { User } from "../lib/types";
import { UserAvatar } from "./UserAvatar";

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
  onFeedback: () => void;
  onProfile: () => void;
  hideScore?: boolean;
}

export function Navbar({ user, onLogout, onFeedback, onProfile, hideScore = false }: NavbarProps) {
  return (
    <nav className="navbar" aria-label="Main navigation">
      <div className="navbar-left">
        <div className="navbar-brand">
          <Link to="/">POI Game</Link>
        </div>
        <div className="navbar-links">
          <Link to="/about" className="nav-link">About</Link>
          {user && <>
            <Link to="/play" className="nav-link">Play</Link>
            <Link to="/leaderboard" className="nav-link">Leaderboard</Link>
            <button type="button" className="nav-link nav-feedback" onClick={onFeedback}>Feedback</button>
          </>}
        </div>
      </div>
        {user ? (
            <div className="navbar-user">
              <button
                type="button"
                className="user-profile-trigger"
                onClick={onProfile}
                aria-label={`View profile for ${user.display_name}`}
                aria-haspopup="dialog"
              >
                <UserAvatar
                  name={user.display_name}
                  url={user.avatar_url}
                  className="avatar"
                  fallbackClassName="avatar--fallback"
                />
                <span className="user-name">{user.display_name}</span>
              </button>
              {!hideScore && <span className="user-score">{user.score} pts</span>}
              <button onClick={onLogout} className="btn btn-sm btn-outline">
                Logout
              </button>
            </div>
        ) : (
          <div className="navbar-auth">
            <Link to="/login" className="btn btn-sm btn-outline">
              Log In
            </Link>
            <Link to="/register" className="btn btn-sm btn-primary">
              Register
            </Link>
          </div>
        )}
    </nav>
  );
}
