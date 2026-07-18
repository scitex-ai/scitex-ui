/**
 * Theme boot — resolve the persisted theme preference BEFORE first paint.
 *
 * Load this SYNCHRONOUSLY in <head> (no defer/async). Deferring it would let
 * the page paint with the wrong theme first, producing a visible flash.
 *
 * The standalone shell used to hardcode data-theme="dark" on <html>, which
 * silently overrode a user's stored light preference on every SciTeX GUI.
 *
 * Keys, in precedence order:
 *   "stx-theme"                — canonical (ThemeProvider's DEFAULT_STORAGE_KEY)
 *   "scitex-theme-preference"  — legacy, read-only fallback for hub/cloud-served
 *                                pages until those converge on the canonical key
 *
 * Default when nothing is stored: dark, overridable per-page via
 * <html data-theme-default="light"> (the shell renders it from the
 * shell_theme_default context var).
 */
(function () {
  var root = document.documentElement;
  var fallback =
    root.getAttribute("data-theme-default") === "light" ? "light" : "dark";
  var theme;
  try {
    theme =
      localStorage.getItem("stx-theme") ||
      localStorage.getItem("scitex-theme-preference");
  } catch (e) {
    /* private mode / storage disabled — fall through to the default */
  }
  if (theme !== "light" && theme !== "dark") theme = fallback;

  root.setAttribute("data-theme", theme);
  // Legacy class contract. On <html> it is applied pre-paint and still matches
  // descendant selectors like `.dark-theme .foo`; mirror it onto <body> once that
  // exists so consumer rules written as `body.dark-theme` keep matching too.
  root.classList.add(theme === "dark" ? "dark-theme" : "light-theme");
  document.addEventListener("DOMContentLoaded", function () {
    document.body.classList.add(theme === "dark" ? "dark-theme" : "light-theme");
  });

  window.__stxTheme = theme;
})();
