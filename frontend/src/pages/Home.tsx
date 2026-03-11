import { Link } from "react-router-dom";
import type { User } from "../lib/types";

interface HomeProps {
  user: User | null;
}

export function Home({ user }: HomeProps) {
  return (
    <div className="page home-page">
      <div className="hero">
        <h1>POI Game</h1>
        <p className="hero-subtitle">
          Help train AI models by identifying Points of Interest from GPS data
        </p>
        {user ? (
          <div className="hero-stats">
            <p>
              Welcome back, <strong>{user.display_name}</strong>!
            </p>
            <div className="stat-cards">
              <div className="stat-card">
                <span className="stat-value">{user.score}</span>
                <span className="stat-label">Points</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{user.answers_count}</span>
                <span className="stat-label">Answers</span>
              </div>
            </div>
            <Link to="/play" className="btn btn-primary btn-lg">
              Continue Playing
            </Link>
          </div>
        ) : (
          <div className="hero-cta">
            <Link to="/register" className="btn btn-primary btn-lg">
              Get Started
            </Link>
            <p className="hero-cta-sub">
              Already have an account? <Link to="/login">Log in</Link>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
