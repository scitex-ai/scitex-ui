/**
 * ProjectSelector — the standard project-picking pattern (compass L625).
 *
 * A dropdown that lists the user's projects, shows the current selection on
 * the trigger, and emits `stx-project-selector:change` (bubbles) when the
 * selection changes.
 *
 * Presentational + behavioural: the DATA comes from the app (it knows the
 * user and their project permissions); this component owns the pattern — the
 * markup, the BEM vocabulary, and the event contract.
 *
 * Options are real `<button>`s, so keyboard operability (Tab, Enter, Space)
 * comes from the platform instead of a hand-rolled key handler — the same
 * philosophy as the form-controls checkbox (theme the native control, do not
 * replace it).
 *
 * Usage:
 *   import { ProjectSelector, PROJECT_SELECTOR_CHANGE } from
 *     "scitex_ui/ts/app/project-selector";
 *
 *   const sel = new ProjectSelector({
 *     container: "#project-select",
 *     projects: [{ id: "scitex-ui", name: "scitex-ui" }],
 *     current: "scitex-ui",
 *   });
 *   sel.container.addEventListener(PROJECT_SELECTOR_CHANGE, (e) => {
 *     const { id, name } = (e as CustomEvent<{ id: string; name: string }>)
 *       .detail;
 *   });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { ProjectSelectorConfig, ProjectOption } from "./types";

const CLS = "stx-app-project-selector";

/** Event emitted on the container when the selection changes. */
export const PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";

export class ProjectSelector extends BaseComponent<ProjectSelectorConfig> {
  private current: ProjectOption | null;
  private trigger: HTMLButtonElement;
  private label: HTMLElement;
  private panel: HTMLElement;
  private list: HTMLElement;
  private open = false;
  private outsideClickHandler: (e: MouseEvent) => void;
  private keyHandler: (e: KeyboardEvent) => void;

  constructor(config: ProjectSelectorConfig) {
    super(config);
    this.current =
      config.projects.find((p) => p.id === config.current) ?? null;

    this.container.className = CLS;

    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className = `${CLS}__trigger`;
    this.trigger.setAttribute("aria-haspopup", "listbox");

    this.label = document.createElement("span");
    this.label.className = `${CLS}__current`;

    this.trigger.appendChild(this.label);
    this.renderLabel();

    this.panel = document.createElement("div");
    this.panel.className = `${CLS}__panel`;
    this.panel.setAttribute("role", "listbox");

    this.list = document.createElement("div");
    this.list.className = `${CLS}__list`;
    this.panel.appendChild(this.list);
    this.renderList();

    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);

    this.trigger.addEventListener("click", () => this.toggle());

    this.outsideClickHandler = (e: MouseEvent): void => {
      if (!this.container.contains(e.target as Node)) {
        this.close();
      }
    };
    this.keyHandler = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }

  /** Render the trigger label (current selection or placeholder). */
  private renderLabel(): void {
    if (this.current) {
      this.label.textContent = this.current.name;
      this.label.className = `${CLS}__current`;
    } else {
      this.label.textContent = this.config.placeholder ?? "Select project";
      this.label.className = `${CLS}__placeholder`;
    }
  }

  /** (Re)build the option list from config.projects. */
  private renderList(): void {
    this.list.innerHTML = "";
    if (this.config.projects.length === 0) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = "No projects";
      this.list.appendChild(empty);
      return;
    }
    for (const project of this.config.projects) {
      const option = document.createElement("button");
      option.type = "button";
      const isCurrent = this.current?.id === project.id;
      option.className = isCurrent
        ? `${CLS}__option ${CLS}__option--current`
        : `${CLS}__option`;
      if (isCurrent) {
        option.setAttribute("aria-current", "true");
      }
      option.setAttribute("role", "option");
      option.setAttribute("aria-selected", String(isCurrent));

      const name = document.createElement("span");
      name.className = `${CLS}__option-name`;
      name.textContent = project.name;
      option.appendChild(name);

      if (project.detail) {
        const detail = document.createElement("span");
        detail.className = `${CLS}__option-detail`;
        detail.textContent = project.detail;
        option.appendChild(detail);
      }

      option.addEventListener("click", () => this.select(project));
      this.list.appendChild(option);
    }
  }

  /** Open or close the option panel. */
  toggle(): void {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }

  close(): void {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }

  /** Select a project: update the trigger, close, and emit the change. */
  private select(project: ProjectOption): void {
    const changed = this.current?.id !== project.id;
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    if (changed) {
      this.emit(PROJECT_SELECTOR_CHANGE, {
        id: project.id,
        name: project.name,
      });
    }
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
}
