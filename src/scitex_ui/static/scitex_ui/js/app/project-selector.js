/* AUTO-GENERATED from ts/app/project-selector/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/project-selector/index.ts --bundle --format=esm --outfile=js/app/project-selector.js */

// ts/_base/BaseComponent.ts
var BaseComponent = class {
  container;
  config;
  constructor(config) {
    this.config = config;
    const el = typeof config.container === "string" ? document.querySelector(config.container) : config.container;
    if (!el) {
      throw new Error(
        `${this.constructor.name}: container not found: ${config.container}`
      );
    }
    this.container = el;
  }
  /** Emit a custom event on the container. */
  emit(name, detail) {
    this.container.dispatchEvent(
      new CustomEvent(name, { detail, bubbles: true })
    );
  }
  /** Destroy the component and clean up DOM. */
  destroy() {
    this.container.innerHTML = "";
  }
};

// ts/app/project-selector/_ProjectSelector.ts
var CLS = "stx-app-project-selector";
var PROJECT_SELECTOR_CHANGE = "stx-project-selector:change";
var ProjectSelector = class extends BaseComponent {
  current;
  trigger;
  label;
  panel;
  list;
  open = false;
  outsideClickHandler;
  keyHandler;
  constructor(config) {
    super(config);
    this.current = config.projects.find((p) => p.id === config.current) ?? null;
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
    this.trigger.addEventListener("click", () => this.toggle());
    this.outsideClickHandler = (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    };
    this.keyHandler = (e) => {
      if (e.key === "Escape") {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }
  /** Render the trigger label (current selection or placeholder). */
  renderLabel() {
    if (this.current) {
      this.label.textContent = this.current.name;
      this.label.className = `${CLS}__current`;
    } else {
      this.label.textContent = this.config.placeholder ?? "Select project";
      this.label.className = `${CLS}__placeholder`;
    }
  }
  /** (Re)build the option list from config.projects. */
  renderList() {
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
      option.className = isCurrent ? `${CLS}__option ${CLS}__option--current` : `${CLS}__option`;
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
  toggle() {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }
  close() {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }
  /** Select a project: update the trigger, close, and emit the change. */
  select(project) {
    const changed = this.current?.id !== project.id;
    this.current = project;
    this.renderLabel();
    this.renderList();
    this.close();
    if (changed) {
      this.emit(PROJECT_SELECTOR_CHANGE, {
        id: project.id,
        name: project.name
      });
    }
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
};
export {
  PROJECT_SELECTOR_CHANGE,
  ProjectSelector
};
