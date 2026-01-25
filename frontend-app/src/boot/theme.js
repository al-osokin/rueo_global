import { boot } from "quasar/wrappers";
import {
  DarkVariant,
  ThemeMode,
  applyTheme,
  detectPreferredTheme,
  getStoredTheme,
  getStoredDarkVariant,
} from "src/utils/theme";

export default boot(() => {
  const stored = getStoredTheme();
  const storedVariant = getStoredDarkVariant();
  const initialVariant =
    storedVariant === DarkVariant.AMOLED
      ? DarkVariant.AMOLED
      : DarkVariant.DEFAULT;
  const initialMode =
    stored === ThemeMode.DARK || stored === ThemeMode.LIGHT
      ? stored
      : detectPreferredTheme();
  applyTheme(initialMode, initialVariant);
  if (typeof document !== "undefined") {
    document.documentElement.removeAttribute("data-initial-theme");
  }
});
