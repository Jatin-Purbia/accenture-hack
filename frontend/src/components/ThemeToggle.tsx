import { Moon, Sun } from "lucide-react";
import type { Theme } from "../lib/theme";

interface Props {
  theme: Theme;
  onChange: (theme: Theme) => void;
}

export function ThemeToggle({ theme, onChange }: Props) {
  const isDark = theme === "dark";
  return (
    <button
      onClick={() => onChange(isDark ? "light" : "dark")}
      className="btn"
      title={isDark ? "Switch to light theme" : "Switch to dark theme"}
      aria-label="Toggle color theme"
      style={{ padding: 9 }}
    >
      {isDark ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}
