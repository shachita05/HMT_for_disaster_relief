// JS-side mirror of the CSS custom properties in index.css -- see
// useColorScheme.ts for why chart color props can't just reference
// var(--...) the way the rest of the UI does. The app is dark-only (no
// light variant), so this always returns the same dark-theme values --
// the `dark` param is kept only so call sites (which still call
// usePrefersDark()) don't need touching if a light theme is ever added back.
export function chartTokens(_dark: boolean) {
  return {
    seriesBlue: "#3987e5",
    good: "#10b981",
    warning: "#ffb100",
    critical: "#ef4444",
    grid: "#273647",
    axis: "#8c909f",
    tooltipBg: "#1e293b",
    tooltipBorder: "#334155",
    tooltipText: "#d4e4fa",
  };
}
