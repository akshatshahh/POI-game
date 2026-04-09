import { type FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, getGoogleLoginUrl } from "../lib/api";
import type { User } from "../lib/types";

interface LoginProps {
  onAuth: () => void;
}

export function Login({ onAuth }: LoginProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [usernameOrEmail, setUsernameOrEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (searchParams.get("error") === "oauth") {
      setError("Google sign-in failed or was cancelled. Please try again.");
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!usernameOrEmail.trim() || !password) {
      setError("Both fields are required");
      return;
    }

    setSubmitting(true);
    try {
      await api.post<{ user: User }>(
        "/auth/login",
        { username_or_email: usernameOrEmail.trim(), password },
      );
      onAuth();
    } catch {
      setError("Invalid username/email or password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page auth-page">
      <div className="auth-card">
        <h2>Log In</h2>
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="usernameOrEmail">Username or Email</label>
            <input
              id="usernameOrEmail"
              type="text"
              value={usernameOrEmail}
              onChange={(e) => setUsernameOrEmail(e.target.value)}
              placeholder="username or you@example.com"
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" disabled={submitting} className="btn btn-primary btn-full">
            {submitting ? "Logging in..." : "Log In"}
          </button>
        </form>
        <div className="auth-divider"><span>or</span></div>
        <a href={getGoogleLoginUrl()} className="btn btn-google btn-full">
          Log in with Google
        </a>
        <p className="auth-switch">
          Don&apos;t have an account? <Link to="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
