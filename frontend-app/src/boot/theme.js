import { boot } from "quasar/wrappers";
import {
  ThemeMode,
  applyTheme,
  detectPreferredTheme,
  getStoredTheme,
} from "src/utils/theme";

export default boot(() => {
  const stored = getStoredTheme();
  const initialMode =
    stored === ThemeMode.DARK || stored === ThemeMode.LIGHT
      ? stored
      : detectPreferredTheme();
  applyTheme(initialMode);
});
