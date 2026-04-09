import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api, getGoogleLoginUrl } from "../lib/api";
import type { User } from "../lib/types";

interface RegisterProps {
  onAuth: () => void;
}

const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export function Register({ onAuth }: RegisterProps) {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = "Name is required";
    if (!USERNAME_RE.test(username))
      errs.username = "3–20 chars: letters, numbers, underscore";
    if (!EMAIL_RE.test(email)) errs.email = "Enter a valid email";
    if (!PASSWORD_RE.test(password))
      errs.password = "Min 8 chars, at least 1 letter and 1 number";
    if (password !== confirmPassword)
      errs.confirmPassword = "Passwords do not match";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      await api.post<{ user: User }>(
        "/auth/register",
        { name: name.trim(), username, email: email.trim().toLowerCase(), password },
      );
      onAuth();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      if (msg.includes("409")) {
        setError("Username or email already taken");
      } else if (msg.includes("422")) {
        setError("Please fix the validation errors above");
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page auth-page">
      <div className="auth-card">
        <h2>Create Account</h2>
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <div className="form-group">
            <label htmlFor="name">Display Name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoComplete="name"
            />
            {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="letters, numbers, underscore"
              autoComplete="username"
            />
            {fieldErrors.username && <span className="field-error">{fieldErrors.username}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
            {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 8 chars, letter + number"
              autoComplete="new-password"
            />
            {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
              autoComplete="new-password"
            />
            {fieldErrors.confirmPassword && (
              <span className="field-error">{fieldErrors.confirmPassword}</span>
            )}
          </div>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" disabled={submitting} className="btn btn-primary btn-full">
            {submitting ? "Creating account..." : "Register"}
          </button>
        </form>
        <div className="auth-divider"><span>or</span></div>
        <a href={getGoogleLoginUrl()} className="btn btn-google btn-full">
          Sign up with Google
        </a>
        <p className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
