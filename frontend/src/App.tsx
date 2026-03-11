import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { Home } from "./pages/Home";
import { Play } from "./pages/Play";
import { Leaderboard } from "./pages/Leaderboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
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
            path="/login"
            element={user ? <Navigate to="/" replace /> : <Login onAuth={refetchUser} />}
          />
          <Route
            path="/register"
            element={user ? <Navigate to="/" replace /> : <Register onAuth={refetchUser} />}
          />
          <Route
            path="/play"
            element={user ? <Play onScoreUpdate={refetchUser} /> : <Navigate to="/login" replace />}
          />
          <Route
            path="/leaderboard"
            element={user ? <Leaderboard /> : <Navigate to="/login" replace />}
          />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
