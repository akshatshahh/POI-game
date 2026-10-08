import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LoadingScreen } from "./components/LoadingScreen";
import { Navbar } from "./components/Navbar";
import { RequireAuth } from "./components/RequireAuth";
import { Home } from "./pages/Home";
import { Play } from "./pages/Play";
import { Leaderboard } from "./pages/Leaderboard";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { useAuth } from "./hooks/useAuth";
import { useEffect, useState } from "react";
import { LogoutFeedback } from "./components/LogoutFeedback";
import { AboutContent } from "./components/AboutContent";
import { UserProfile } from "./components/UserProfile";

function AppShell({
  user,
  loading,
  logout,
  refetchUser,
  refreshUser,
}: ReturnType<typeof useAuth>) {
  const location = useLocation();
  const [feedbackMode, setFeedbackMode] = useState<"logout" | "feedback" | null>(null);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const isPlay = location.pathname === "/play";

  useEffect(() => {
    if (!feedbackSaved) return;
    const timeout = window.setTimeout(() => setFeedbackSaved(false), 5000);
    return () => window.clearTimeout(timeout);
  }, [feedbackSaved]);

  // Wait for /auth/me before rendering any route — prevents protected pages
  // from briefly mounting (and calling game APIs) while auth is unknown.
  if (loading) {
    return (
      <LoadingScreen
        label="Signing you in"
        detail="Please wait while we get your game ready."
      />
    );
  }

  return (
    <div className={isPlay ? "app-shell app-shell--play" : "app-shell"}>
      <Navbar user={user} onLogout={() => {
        setProfileOpen(false);
        setFeedbackMode("logout");
      }} onFeedback={() => {
        setProfileOpen(false);
        setFeedbackSaved(false);
        setFeedbackMode("feedback");
      }} onProfile={() => {
        setFeedbackMode(null);
        setProfileOpen(true);
      }} hideScore={isPlay} />
      {feedbackMode && user && <LogoutFeedback mode={feedbackMode} onComplete={feedbackMode === "logout" ? logout : async () => {
        setFeedbackMode(null);
        setFeedbackSaved(true);
      }} onCancel={() => setFeedbackMode(null)} />}
      {profileOpen && user && <UserProfile user={user} onClose={() => setProfileOpen(false)} />}
      {feedbackSaved && <p className="feedback-confirmation" role="status">Thanks for your feedback.</p>}
      <main className={isPlay ? "main-content main-content--play" : "main-content"}>
        <Routes>
          {/* Public */}
          <Route path="/" element={<Home user={user} />} />
          <Route path="/about" element={<div className="page"><AboutContent /></div>} />
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
                <Play
                  userId={user?.id ?? ""}
                  currentScore={user?.score ?? 0}
                  isFirstTimePlayer={user?.answers_count === 0}
                  onScoreUpdate={refreshUser}
                  paused={feedbackMode !== null || profileOpen}
                />
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
    </div>
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
