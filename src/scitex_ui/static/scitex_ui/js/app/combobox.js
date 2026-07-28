// src/scitex_ui/static/scitex_ui/ts/_base/BaseComponent.ts
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

// src/scitex_ui/static/scitex_ui/ts/_base/fuzzy.ts
function fuzzyMatch(query, hay) {
  if (!query) return true;
  let i = 0;
  for (const c of query) {
    const found = hay.indexOf(c, i);
    if (found < 0) return false;
    i = found + 1;
  }
  return true;
}

// src/scitex_ui/static/scitex_ui/ts/app/combobox/_Combobox.ts
var CLS = "stx-app-combobox";
var Combobox = class _Combobox extends BaseComponent {
  triggerEl;
  menuEl = null;
  inputEl = null;
  listEl = null;
  open = false;
  currentValue;
  highlightedIndex = -1;
  filtered = [];
  outsideClickHandler;
  constructor(config) {
    super(config);
    this.currentValue = config.value;
    this.triggerEl = typeof config.trigger === "string" ? document.querySelector(config.trigger) : config.trigger;
    if (!this.triggerEl) {
      throw new Error(`Combobox: trigger not found: ${config.trigger}`);
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
    this.syncTriggerLabel();
  }
  /** Open the combobox popover. */
  show() {
    if (this.open) return;
    this.open = true;
    this.renderMenu();
    this.container.style.display = "block";
    this.positionMenu();
    requestAnimationFrame(() => this.inputEl?.focus());
  }
  /** Close the combobox popover. */
  close() {
    if (!this.open) return;
    this.open = false;
    this.container.style.display = "none";
    this.highlightedIndex = -1;
  }
  /** Toggle open / close. */
  toggle() {
    this.open ? this.close() : this.show();
  }
  /** Replace the option list (e.g. after the consumer created a new
   *  value via onCreate and now wants to include it). */
  setItems(items) {
    this.config.items = items;
    if (this.open) {
      this.applyFilter(this.inputEl?.value || "");
      this.renderList();
    }
  }
  /** Programmatically set the selected value. Does NOT fire onChange. */
  setValue(value) {
    this.currentValue = value;
    this.syncTriggerLabel();
  }
  /** Get the currently selected value. */
  getValue() {
    return this.currentValue;
  }
  destroy() {
    document.removeEventListener("click", this.outsideClickHandler);
    super.destroy();
  }
  // ----- Render -------------------------------------------------------
  renderMenu() {
    this.container.innerHTML = "";
    this.container.className = CLS;
    const menu = document.createElement("div");
    menu.className = `${CLS}__menu`;
    menu.setAttribute("role", "listbox");
    const input = document.createElement("input");
    input.type = "text";
    input.className = `${CLS}__input`;
    input.placeholder = this.config.placeholder || "Search\u2026";
    input.autocomplete = "off";
    input.spellcheck = false;
    input.setAttribute("aria-autocomplete", "list");
    input.addEventListener("input", () => {
      this.applyFilter(input.value);
      this.highlightedIndex = this.filtered.length ? 0 : -1;
      this.renderList();
    });
    input.addEventListener("keydown", (e) => this.onInputKeydown(e));
    menu.appendChild(input);
    this.inputEl = input;
    const list = document.createElement("div");
    list.className = `${CLS}__list`;
    menu.appendChild(list);
    this.listEl = list;
    this.container.appendChild(menu);
    this.menuEl = menu;
    this.applyFilter("");
    this.highlightedIndex = this.filtered.length ? 0 : -1;
    this.renderList();
  }
  renderList() {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";
    if (!this.filtered.length) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = this.config.emptyText || "No matches";
      this.listEl.appendChild(empty);
    } else {
      let lastGroup = void 0;
      this.filtered.forEach((entry, idx) => {
        const { item } = entry;
        if (item.group && item.group !== lastGroup) {
          const hdr = document.createElement("div");
          hdr.className = `${CLS}__group`;
          hdr.textContent = item.group;
          this.listEl.appendChild(hdr);
          lastGroup = item.group;
        } else if (!item.group) {
          lastGroup = void 0;
        }
        const row = document.createElement("div");
        row.className = `${CLS}__item`;
        row.setAttribute("role", "option");
        row.dataset.value = item.value;
        if (item.disabled) row.classList.add(`${CLS}__item--disabled`);
        if (idx === this.highlightedIndex) {
          row.classList.add(`${CLS}__item--highlighted`);
        }
        if (this.currentValue === item.value) {
          row.classList.add(`${CLS}__item--selected`);
        }
        row.textContent = item.label;
        if (!item.disabled) {
          row.addEventListener("mouseenter", () => {
            this.highlightedIndex = idx;
            this.refreshHighlight();
          });
          row.addEventListener("click", (e) => {
            e.stopPropagation();
            this.select(entry);
          });
        }
        this.listEl.appendChild(row);
      });
    }
    const rawQuery = this.inputEl?.value || "";
    const q = rawQuery.trim();
    if (this.config.onCreate && q.length > 0) {
      const exists = this.config.items.some(
        (it) => it.label.toLowerCase() === q.toLowerCase()
      );
      if (!exists) {
        const labelFn = this.config.createLabel || ((raw) => `+ Create \u201C${raw}\u201D`);
        const row = document.createElement("div");
        row.className = `${CLS}__item ${CLS}__item--create`;
        row.setAttribute("role", "option");
        row.textContent = labelFn(q);
        row.addEventListener("click", (e) => {
          e.stopPropagation();
          this.config.onCreate?.(q);
          this.close();
        });
        this.listEl.appendChild(row);
      }
    }
  }
  refreshHighlight() {
    if (!this.listEl) return;
    this.listEl.querySelectorAll(`.${CLS}__item--highlighted`).forEach((el) => el.classList.remove(`${CLS}__item--highlighted`));
    const rows = this.listEl.querySelectorAll(`.${CLS}__item`);
    const target = rows[this.highlightedIndex];
    if (target) {
      target.classList.add(`${CLS}__item--highlighted`);
      target.scrollIntoView({ block: "nearest" });
    }
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
  syncTriggerLabel() {
    if (this.config.updateTriggerLabel === false) return;
    const item = this.config.items.find((it) => it.value === this.currentValue);
    if (item) {
      this.triggerEl.textContent = item.label;
    }
  }
  // ----- Behaviour ----------------------------------------------------
  onInputKeydown(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (this.filtered.length) {
        this.highlightedIndex = Math.min(
          this.filtered.length - 1,
          this.highlightedIndex + 1
        );
        this.refreshHighlight();
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (this.filtered.length) {
        this.highlightedIndex = Math.max(0, this.highlightedIndex - 1);
        this.refreshHighlight();
      }
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      if (this.highlightedIndex >= 0 && this.highlightedIndex < this.filtered.length) {
        this.select(this.filtered[this.highlightedIndex]);
      } else if (this.config.onCreate) {
        const q = (this.inputEl?.value || "").trim();
        if (q.length > 0) {
          const exists = this.config.items.some(
            (it) => it.label.toLowerCase() === q.toLowerCase()
          );
          if (!exists) {
            this.config.onCreate(q);
            this.close();
          }
        }
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      this.close();
      this.triggerEl.focus?.();
      return;
    }
  }
  select(entry) {
    if (entry.item.disabled) return;
    this.currentValue = entry.item.value;
    this.syncTriggerLabel();
    this.config.onChange?.(entry.item);
    this.emit("combobox:change", { value: entry.item.value, item: entry.item });
    this.close();
  }
  applyFilter(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
      this.filtered = this.config.items.map((item, index) => ({ item, index }));
      return;
    }
    const fuzzy = this.config.fuzzy !== false;
    const out = [];
    this.config.items.forEach((item, index) => {
      const hay = `${item.label} ${item.value} ${item.group || ""}`.toLowerCase();
      const match = fuzzy ? _Combobox.fuzzyMatch(q, hay) : hay.includes(q);
      if (match) out.push({ item, index });
    });
    this.filtered = out;
  }
  /** fzf-style subsequence match. Delegates to the shared implementation in
   *  `_base/fuzzy` so Combobox and Dropdown cannot drift apart — a list that
   *  filters differently from the one next to it teaches users to distrust
   *  both. Kept as a static method because it is part of the public surface. */
  static fuzzyMatch(query, hay) {
    return fuzzyMatch(query, hay);
  }
};
export {
  Combobox
};
