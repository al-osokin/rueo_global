import { Dark, LocalStorage } from "quasar";

export const ThemeMode = Object.freeze({
  LIGHT: "light",
  DARK: "dark",
});

export const THEME_STORAGE_KEY = "rueo_theme_preference";

const THEME_META_COLORS = {
  [ThemeMode.LIGHT]: "#ffffff",
  [ThemeMode.DARK]: "#0b1c2b",
};

function hasWindow() {
  return typeof window !== "undefined";
}

export function detectPreferredTheme() {
  if (hasWindow() && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? ThemeMode.DARK
      : ThemeMode.LIGHT;
  }
  return ThemeMode.LIGHT;
}

export function getStoredTheme() {
  return LocalStorage.getItem(THEME_STORAGE_KEY);
}

export function persistThemePreference(mode) {
  LocalStorage.set(THEME_STORAGE_KEY, mode);
}

export function clearThemePreference() {
  LocalStorage.remove(THEME_STORAGE_KEY);
}

export function applyTheme(mode) {
  Dark.set(mode === ThemeMode.DARK);
  updateMetaThemeColor(mode);
}

export function updateMetaThemeColor(mode) {
  if (typeof document === "undefined") {
    return;
  }
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", THEME_META_COLORS[mode] || THEME_META_COLORS[ThemeMode.LIGHT]);
  }
}

export function listenToSystemThemeChange(callback) {
  if (!hasWindow() || !window.matchMedia) {
    return () => {};
  }
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = (event) => {
    callback(event.matches ? ThemeMode.DARK : ThemeMode.LIGHT);
  };
  if (mediaQuery.addEventListener) {
    mediaQuery.addEventListener("change", handler);
  } else if (mediaQuery.addListener) {
    mediaQuery.addListener(handler);
  }

  return () => {
    if (mediaQuery.removeEventListener) {
      mediaQuery.removeEventListener("change", handler);
    } else if (mediaQuery.removeListener) {
      mediaQuery.removeListener(handler);
    }
  };
}
