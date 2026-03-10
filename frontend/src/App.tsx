import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { Home } from "./pages/Home";
import { Play } from "./pages/Play";
import { Leaderboard } from "./pages/Leaderboard";
import { useAuth } from "./hooks/useAuth";

function App() {
  const { user, loading, logout, refetchUser } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Navbar user={user} onLogout={logout} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Home user={user} />} />
          <Route
            path="/play"
            element={user ? <Play onScoreUpdate={refetchUser} /> : <Navigate to="/" replace />}
          />
          <Route path="/leaderboard" element={<Leaderboard />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
