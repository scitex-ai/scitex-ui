/* AUTO-GENERATED from ts/app/dropdown/index.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/dropdown/index.ts --bundle --format=esm --outfile=js/app/dropdown.js */
var __defProp = Object.defineProperty;
var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

// ts/_base/BaseComponent.ts
var BaseComponent = class {
  constructor(config) {
    __publicField(this, "container");
    __publicField(this, "config");
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

// ts/app/dropdown/_Dropdown.ts
var CLS = "stx-app-dropdown";
var Dropdown = class extends BaseComponent {
  constructor(config) {
    super(config);
    __publicField(this, "triggerEl");
    __publicField(this, "menuEl", null);
    __publicField(this, "open", false);
    __publicField(this, "outsideClickHandler");
    this.triggerEl = typeof config.trigger === "string" ? document.querySelector(config.trigger) : config.trigger;
    if (!this.triggerEl) {
      throw new Error(`Dropdown: trigger not found: ${config.trigger}`);
    }
    this.outsideClickHandler = (e) => {
      const target = e.target;
      if (this.open && !this.container.contains(target) && !this.triggerEl.contains(target)) {
        this.close();
      }
    };
    this.triggerEl.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggle();
    });
    document.addEventListener("click", this.outsideClickHandler);
  }
  /** Open the dropdown. */
  show() {
    if (this.open) return;
    this.open = true;
    this.renderMenu();
    this.container.style.display = "block";
    this.positionMenu();
  }
  /** Close the dropdown. */
  close() {
    if (!this.open) return;
    this.open = false;
    this.container.style.display = "none";
  }
  /** Toggle open/close. */
  toggle() {
    this.open ? this.close() : this.show();
  }
  /** Update items dynamically. */
  setItems(items) {
    this.config.items = items;
    if (this.open) this.renderMenu();
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    super.destroy();
  }
  renderMenu() {
    this.container.innerHTML = "";
    this.container.className = CLS;
    const menu = document.createElement("ul");
    menu.className = `${CLS}__menu`;
    for (const item of this.config.items) {
      if (item.separator) {
        const sep = document.createElement("li");
        sep.className = `${CLS}__separator`;
        menu.appendChild(sep);
        continue;
      }
      const li = document.createElement("li");
      li.className = `${CLS}__item`;
      if (item.disabled) li.classList.add(`${CLS}__item--disabled`);
      if (item.icon) {
        const icon = document.createElement("i");
        icon.className = item.icon;
        li.appendChild(icon);
      }
      const label = document.createElement("span");
      label.textContent = item.label;
      li.appendChild(label);
      if (!item.disabled) {
        li.addEventListener("click", (e) => {
          e.stopPropagation();
          this.close();
          item.onClick?.();
          this.config.onSelect?.(item);
        });
      }
      menu.appendChild(li);
    }
    this.container.appendChild(menu);
    this.menuEl = menu;
  }
  positionMenu() {
    const rect = this.triggerEl.getBoundingClientRect();
    this.container.style.position = "absolute";
    this.container.style.top = `${rect.bottom + window.scrollY}px`;
    if (this.config.align === "right") {
      this.container.style.right = `${window.innerWidth - rect.right}px`;
      this.container.style.left = "auto";
    } else {
      this.container.style.left = `${rect.left + window.scrollX}px`;
      this.container.style.right = "auto";
    }
    this.container.style.zIndex = "100";
  }
};
export {
  Dropdown
};
