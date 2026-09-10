/**
 * Type definitions for the ProjectSelector component.
 *
 * The ProjectSelector is the standard project-picking pattern (compass L625):
 * a dropdown that lists the user's projects, shows the current selection on
 * the trigger, and emits a change event when the selection changes.
 *
 * The generic Combobox is a near-miss for this: it is search-first and
 * value-based, built for long option lists. Projects are a short, ordered,
 * identity-bearing list, so a plain dropdown with a visible current
 * selection is the right shape.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface ProjectOption {
  /** Stable project identifier (passed back via the change event). */
  id: string;
  /** Display name (what the user sees on the trigger and in the list). */
  name: string;
  /** Optional secondary line under the name (path, host, status...). */
  detail?: string;
}

export interface ProjectSelectorConfig extends BaseComponentConfig {
  /** The user's projects, in display order. The DATA comes from the app —
   * it knows the user and their project permissions; this component owns
   * the pattern (markup, vocabulary, event contract), not the data. */
  projects: ProjectOption[];
  /** Currently selected project id, if any. */
  current?: string | null;
  /** Placeholder shown on the trigger when nothing is selected.
   * Defaults to "Select project". */
  placeholder?: string;
}
