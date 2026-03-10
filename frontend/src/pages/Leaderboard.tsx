import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { LeaderboardEntry } from "../lib/types";

export function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const data = await api.get<LeaderboardEntry[]>("/leaderboard?limit=50");
        setEntries(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load leaderboard");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="page leaderboard-page">
        <div className="loading-screen" style={{ height: "auto", paddingTop: "4rem" }}>
          <div className="spinner" />
          <p>Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page leaderboard-page">
      <h2>Leaderboard</h2>
      {error && <p className="error-text">{error}</p>}
      {entries.length === 0 && !error ? (
        <p className="placeholder-text">No players on the leaderboard yet. Be the first!</p>
      ) : (
        <div className="leaderboard-table-wrapper">
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th className="col-rank">#</th>
                <th className="col-player">Player</th>
                <th className="col-answers">Answers</th>
                <th className="col-score">Score</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.rank} className={entry.rank <= 3 ? `top-${entry.rank}` : ""}>
                  <td className="col-rank">
                    <span className={`rank-badge ${entry.rank <= 3 ? "rank-top" : ""}`}>
                      {entry.rank <= 3 ? ["🥇", "🥈", "🥉"][entry.rank - 1] : entry.rank}
                    </span>
                  </td>
                  <td className="col-player">
                    <div className="player-info">
                      {entry.avatar_url && (
                        <img src={entry.avatar_url} alt="" className="avatar" />
                      )}
                      <span>{entry.display_name}</span>
                    </div>
                  </td>
                  <td className="col-answers">{entry.answers_count}</td>
                  <td className="col-score">{entry.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
