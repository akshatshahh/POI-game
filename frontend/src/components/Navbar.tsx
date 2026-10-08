import { Link } from "react-router-dom";
import { safeAvatarUrl } from "../lib/api";
import type { User } from "../lib/types";

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
  hideScore?: boolean;
}

export function Navbar({ user, onLogout, hideScore = false }: NavbarProps) {
  const avatar = user ? safeAvatarUrl(user.avatar_url) : null;
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
          </>}
        </div>
      </div>
        {user ? (
            <div className="navbar-user">
              {avatar && (
                <img
                  src={avatar}
                  alt=""
                  className="avatar"
                  referrerPolicy="no-referrer"
                />
              )}
              <span className="user-name">{user.display_name}</span>
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
