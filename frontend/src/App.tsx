import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Navbar } from "./components/Navbar";
import { Home } from "./pages/Home";
import { Play } from "./pages/Play";
import { Leaderboard } from "./pages/Leaderboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { useAuth } from "./hooks/useAuth";

function AppShell({ user, loading, logout, refetchUser }: ReturnType<typeof useAuth>) {
  const location = useLocation();
  const isPlay = location.pathname === "/play";

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <>
      <Navbar user={user} onLogout={logout} />
      <main className={isPlay ? "main-content main-content--play" : "main-content"}>
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
    </>
  );
}

function App() {
  const auth = useAuth();
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppShell {...auth} />
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
