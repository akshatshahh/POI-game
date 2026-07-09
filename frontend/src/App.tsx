import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Navbar } from "./components/Navbar";
import { RequireAuth } from "./components/RequireAuth";
import { Home } from "./pages/Home";
import { Play } from "./pages/Play";
import { Leaderboard } from "./pages/Leaderboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { useAuth } from "./hooks/useAuth";

function AppShell({ user, loading, logout, refetchUser }: ReturnType<typeof useAuth>) {
  const location = useLocation();
  const isPlay = location.pathname === "/play";

  // Wait for /auth/me before rendering any route — prevents protected pages
  // from briefly mounting (and calling game APIs) while auth is unknown.
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
          {/* Public */}
          <Route path="/" element={<Home user={user} />} />
          <Route
            path="/login"
            element={user ? <Navigate to="/" replace /> : <Login onAuth={refetchUser} />}
          />
          <Route
            path="/register"
            element={user ? <Navigate to="/" replace /> : <Register onAuth={refetchUser} />}
          />

          {/* Auth required — unauthenticated users go to home, not the game */}
          <Route
            path="/play"
            element={
              <RequireAuth user={user}>
                <Play onScoreUpdate={refetchUser} />
              </RequireAuth>
            }
          />
          <Route
            path="/leaderboard"
            element={
              <RequireAuth user={user}>
                <Leaderboard />
              </RequireAuth>
            }
          />

          {/* Unknown paths → home */}
          <Route path="*" element={<Navigate to="/" replace />} />
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
