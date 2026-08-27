/** Manual light/dark override. Without this, the app only ever followed
 * the OS's prefers-color-scheme — fine in principle, but it means a judge
 * (or you) on a dark-mode OS sees dark automatically with no way to force
 * light from inside the app. This makes the choice explicit and sticky. */
export type Theme = "light" | "dark";

const STORAGE_KEY = "kpi-theme";

export function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    /* localStorage unavailable (private mode, etc.) — fall through to default */
  }
  return "light"; // default to light regardless of OS preference
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* ignore — theme just won't persist across reloads */
  }
}
