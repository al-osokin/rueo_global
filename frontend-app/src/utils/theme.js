import { Dark, LocalStorage } from "quasar";

export const ThemeMode = Object.freeze({
  LIGHT: "light",
  DARK: "dark",
});

export const DarkVariant = Object.freeze({
  DEFAULT: "default",
  AMOLED: "amoled",
});

export const THEME_STORAGE_KEY = "rueo_theme_preference";
export const DARK_VARIANT_STORAGE_KEY = "rueo_theme_dark_variant";

const THEME_META_COLORS = {
  [ThemeMode.LIGHT]: "#ffffff",
  [ThemeMode.DARK]: "#0b1c2b",
};

const AMOLED_META_COLOR = "#000000";
const DARK_VARIANT_CLASS = "body--amoled";

function hasWindow() {
  return typeof window !== "undefined";
}

function hasDocument() {
  return typeof document !== "undefined";
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

export function getStoredDarkVariant() {
  return LocalStorage.getItem(DARK_VARIANT_STORAGE_KEY);
}

export function persistThemePreference(mode) {
  LocalStorage.set(THEME_STORAGE_KEY, mode);
}

export function persistDarkVariant(variant) {
  LocalStorage.set(DARK_VARIANT_STORAGE_KEY, variant);
}

export function clearThemePreference() {
  LocalStorage.remove(THEME_STORAGE_KEY);
}

export function clearDarkVariant() {
  LocalStorage.remove(DARK_VARIANT_STORAGE_KEY);
}

export function applyTheme(mode, darkVariant = DarkVariant.DEFAULT) {
  Dark.set(mode === ThemeMode.DARK);
  updateBodyAmoledClass(mode, darkVariant);
  updateMetaThemeColor(mode, darkVariant);
}

export function updateMetaThemeColor(mode, darkVariant = DarkVariant.DEFAULT) {
  if (!hasDocument()) {
    return;
  }
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    const metaColor =
      mode === ThemeMode.DARK && darkVariant === DarkVariant.AMOLED
        ? AMOLED_META_COLOR
        : THEME_META_COLORS[mode] || THEME_META_COLORS[ThemeMode.LIGHT];
    meta.setAttribute("content", metaColor);
  }
}

function updateBodyAmoledClass(mode, darkVariant) {
  if (!hasDocument() || !document.body) {
    return;
  }
  const enableAmoled =
    mode === ThemeMode.DARK && darkVariant === DarkVariant.AMOLED;
  document.body.classList.toggle(DARK_VARIANT_CLASS, enableAmoled);
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
