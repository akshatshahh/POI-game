import type { CSSProperties } from "react";

interface LoadingScreenProps {
  label: string;
  detail?: string;
  style?: CSSProperties;
}

/** Centered spinner with a label, used while a page waits on the API. */
export function LoadingScreen({ label, detail, style }: LoadingScreenProps) {
  return (
    <div className="loading-screen" style={style} role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <div className="loading-message">
        <p className="loading-message-title">{label}</p>
        {detail && <p className="loading-message-detail">{detail}</p>}
      </div>
    </div>
  );
}
