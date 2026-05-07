import type { GpsPoint } from "../lib/types";

interface ClockPanelProps {
  gpsPoint: GpsPoint;
}

function parseTime(time: string | null | undefined): { hours: number; minutes: number } | null {
  if (!time) return null;
  const match = time.trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
  if (!match) return null;
  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const period = match[3]?.toUpperCase();
  if (period === "PM" && hours < 12) hours += 12;
  if (period === "AM" && hours === 12) hours = 0;
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
  return { hours, minutes };
}

function ClockFace({ hours, minutes }: { hours: number; minutes: number }) {
  const hourAngle = ((hours % 12) + minutes / 60) * 30 - 90;
  const minuteAngle = minutes * 6 - 90;
  const hourRad = (hourAngle * Math.PI) / 180;
  const minRad = (minuteAngle * Math.PI) / 180;

  const numbers = [
    { n: 12, x: 100, y: 28 },
    { n: 1, x: 136, y: 38 },
    { n: 2, x: 162, y: 64 },
    { n: 3, x: 172, y: 100 },
    { n: 4, x: 162, y: 136 },
    { n: 5, x: 136, y: 162 },
    { n: 6, x: 100, y: 172 },
    { n: 7, x: 64, y: 162 },
    { n: 8, x: 38, y: 136 },
    { n: 9, x: 28, y: 100 },
    { n: 10, x: 38, y: 64 },
    { n: 11, x: 64, y: 38 },
  ];

  return (
    <svg viewBox="0 0 200 200" width="100%" height="100%" role="img" aria-label="Clock face">
      <circle cx="100" cy="100" r="92" fill="#fff" stroke="#0f172a" strokeWidth="3" />
      {Array.from({ length: 60 }).map((_, i) => {
        const isHour = i % 5 === 0;
        const a = (i * 6 - 90) * (Math.PI / 180);
        const inner = isHour ? 80 : 84;
        const outer = 88;
        return (
          <line
            key={i}
            x1={100 + Math.cos(a) * inner}
            y1={100 + Math.sin(a) * inner}
            x2={100 + Math.cos(a) * outer}
            y2={100 + Math.sin(a) * outer}
            stroke="#0f172a"
            strokeWidth={isHour ? 2 : 1}
            strokeLinecap="round"
          />
        );
      })}
      {numbers.map(({ n, x, y }) => (
        <text
          key={n}
          x={x}
          y={y}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="18"
          fontWeight="600"
          fill="#0f172a"
          fontFamily="system-ui, sans-serif"
        >
          {n}
        </text>
      ))}
      <line
        x1="100"
        y1="100"
        x2={100 + Math.cos(hourRad) * 45}
        y2={100 + Math.sin(hourRad) * 45}
        stroke="#0f172a"
        strokeWidth="6"
        strokeLinecap="round"
      />
      <line
        x1="100"
        y1="100"
        x2={100 + Math.cos(minRad) * 65}
        y2={100 + Math.sin(minRad) * 65}
        stroke="#0f172a"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle cx="100" cy="100" r="4" fill="#0f172a" />
    </svg>
  );
}

export function ClockPanel({ gpsPoint }: ClockPanelProps) {
  const parsed = parseTime(gpsPoint.local_time);
  if (!parsed && !gpsPoint.local_time && !gpsPoint.weekday && !gpsPoint.local_date) return null;

  return (
    <div className="clock-panel" aria-label="Visit time">
      {parsed && (
        <div className="clock-panel-face">
          <ClockFace hours={parsed.hours} minutes={parsed.minutes} />
        </div>
      )}
      {gpsPoint.local_time && <div className="clock-panel-time">{gpsPoint.local_time}</div>}
      {(gpsPoint.weekday || gpsPoint.local_date) && (
        <div className="clock-panel-date">
          {[gpsPoint.weekday, gpsPoint.local_date].filter(Boolean).join(", ")}
        </div>
      )}
    </div>
  );
}
