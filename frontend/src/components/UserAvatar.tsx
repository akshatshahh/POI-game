import { useState } from "react";
import { safeAvatarUrl } from "../lib/api";

interface UserAvatarProps {
  name: string;
  url: string | null;
  className: string;
  fallbackClassName: string;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join("");
}

export function UserAvatar({ name, url, className, fallbackClassName }: UserAvatarProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const avatar = safeAvatarUrl(url);

  if (!avatar || imageFailed) {
    return (
      <span className={`${className} ${fallbackClassName}`} aria-hidden="true">
        {initials(name)}
      </span>
    );
  }

  return (
    <img
      src={avatar}
      alt=""
      className={className}
      referrerPolicy="no-referrer"
      onError={() => setImageFailed(true)}
    />
  );
}
