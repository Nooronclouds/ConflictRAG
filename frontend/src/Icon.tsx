// Tiny inline-SVG icon set (no external icon dependency).
const PATHS: Record<string, JSX.Element> = {
  folder: <path d="M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2z" fill="currentColor" stroke="none" />,
  file: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
  up: <><path d="M12 19V6" /><path d="M6 12l6-6 6 6" /></>,
  chev: <path d="M9 6l6 6-6 6" />,
  chevd: <path d="M6 9l6 6 6-6" />,
  back: <path d="M15 6l-6 6 6 6" />,
  fwd: <path d="M9 6l6 6-6 6" />,
  refresh: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4" /></>,
  new: <path d="M12 5v14M5 12h14" />,
  sort: <path d="M4 7h13M4 12h9M4 17h5" />,
  view: <><rect x="4" y="4" width="7" height="7" rx="1" /><rect x="13" y="4" width="7" height="7" rx="1" /><rect x="4" y="13" width="7" height="7" rx="1" /><rect x="13" y="13" width="7" height="7" rx="1" /></>,
  home: <><path d="M4 11l8-7 8 7" /><path d="M6 10v9h12v-9" /></>,
  robot: <><rect x="4" y="8" width="16" height="11" rx="2" /><path d="M12 8V4M8 13h.01M16 13h.01" /></>,
  clip: <path d="M21 11l-8.5 8.5a4 4 0 0 1-6-6L14 5.5a2.5 2.5 0 0 1 4 4l-8.5 8.5" />,
  send: <><path d="M12 19V6M6 12l6-6 6 6" /></>,
  hist: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 4v4h4M12 8v4l3 2" /></>,
  open: <><path d="M14 4h6v6M20 4l-8 8" /><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" /></>,
  check: <path d="M5 12l5 5L20 6" />,
  trash: <><path d="M4 7h16" /><path d="M10 11v6M14 11v6" /><path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" /><path d="M9 7V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3" /></>,
  close: <path d="M6 6l12 12M18 6L6 18" />,
};

export function Icon({ name, size = 16, className, color }: { name: string; size?: number; className?: string; color?: string }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round"
      className={className} style={color ? { color } : undefined}
    >
      {PATHS[name]}
    </svg>
  );
}
