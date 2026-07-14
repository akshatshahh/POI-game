import type { CSSProperties } from "react";

interface LoadingScreenProps {
  label: string;
  style?: CSSProperties;
}

/** Centered spinner with a label, used while a page waits on the API. */
export function LoadingScreen({ label, style }: LoadingScreenProps) {
  return (
    <div className="loading-screen" style={style}>
      <div className="spinner" />
      <p>{label}</p>
    </div>
  );
}
