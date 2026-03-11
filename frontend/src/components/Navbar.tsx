import { Link } from "react-router-dom";
import type { User } from "../lib/types";

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
}

export function Navbar({ user, onLogout }: NavbarProps) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/">🎯 POI Game</Link>
      </div>
      <div className="navbar-links">
        {user ? (
          <>
            <Link to="/play" className="nav-link">
              Play
            </Link>
            <Link to="/leaderboard" className="nav-link">
              Leaderboard
            </Link>
            <div className="navbar-user">
              {user.avatar_url && (
                <img src={user.avatar_url} alt="" className="avatar" />
              )}
              <span className="user-name">{user.display_name}</span>
              <span className="user-score">{user.score} pts</span>
              <button onClick={onLogout} className="btn btn-sm btn-outline">
                Logout
              </button>
            </div>
          </>
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
      </div>
    </nav>
  );
}
