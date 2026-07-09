import { Navigate, useLocation } from "react-router-dom";
import type { User } from "../lib/types";

interface RequireAuthProps {
  user: User | null;
  children: React.ReactNode;
}

/** Blocks protected pages when logged out — sends the user to the home screen. */
export function RequireAuth({ user, children }: RequireAuthProps) {
  const location = useLocation();
  if (!user) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
