import { getGoogleLoginUrl } from "../lib/api";
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
            <a href="/play" className="btn btn-primary btn-lg">
              Continue Playing
            </a>
          </div>
        ) : (
          <div className="hero-cta">
            <a href={getGoogleLoginUrl()} className="btn btn-primary btn-lg">
              Sign in with Google to Play
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
