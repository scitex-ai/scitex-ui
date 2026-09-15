/**
 * AppHelp — the in-app "How to use" primitive.
 *
 * ONE data source feeds both UIs:
 *   - the `?` help panel (a slide-over listing every step, always available)
 *   - the first-open coach-mark tour (highlights each `target` in turn, runs
 *     once per app unless the user replays it)
 *
 * The guide comes from a `<script type="application/json"
 * id="stx-app-help-<app>">` element the leaf app declares (or the
 * `{% stx_help %}` template tag emits). Steps are EN/JA via the per-language
 * `title`/`body` shape. A step with a `target` selector is a tour stop; a
 * step without one is plain panel content.
 *
 * Self-contained like app/panes: BEM `stx-app-help`, vanilla TS, no
 * framework. First-open state is `localStorage["stx-help:<app>:done"]` —
 * the same per-app namespace pattern as panes' `stx-panes:<app>`.
 */

import { gettext } from "../../_base/gettext";
import type {
  AppHelpOptions,
  HelpChangeDetail,
  HelpGuide,
  HelpStorage,
  HelpStep,
} from "./types";

export const HELP_ATTRIBUTE = "data-stx-help";
export const HELP_CHANGE = "stx-app-help:change";
export const STORAGE_PREFIX = "stx-help:";
export const SCRIPT_ID_PREFIX = "stx-app-help-";

const CLS = "stx-app-help";
const CLS_BUTTON = `${CLS}__button`;
const CLS_PANEL = `${CLS}__panel`;
const CLS_PANEL_BODY = `${CLS}__panel-body`;
const CLS_TOUR = `${CLS}__tour`;
const CLS_TOUR_BUBBLE = `${CLS}__tour-bubble`;
const CLS_TOUR_HIGHLIGHT = `${CLS}__tour-highlight`;
const CLS_STEP = `${CLS}__step`;
const CLS_STEP_ICON = `${CLS}__step-icon`;
const CLS_STEP_TITLE = `${CLS}__step-title`;
const CLS_STEP_BODY = `${CLS}__step-body`;
const CLS_CLOSE = `${CLS}__close`;
const CLS_COUNT = `${CLS}__count`;
const CLS_NAV = `${CLS}__nav`;

/** Read the active language: document lang, else "en". */
export function activeLanguage(doc: Document = document): string {
  const lang = doc.documentElement?.getAttribute("lang")?.toLowerCase() ?? "";
  const base = lang.split("-")[0] || "en";
  return base;
}

/** Resolve a step's text for the active language, falling back to English. */
export function stepText(text: HelpStep["title"] | undefined, lang: string): string {
  if (text === undefined) return "";
  if (typeof text === "string") return gettext(text);
  return gettext(text[lang] ?? text.en ?? "");
}

function slug(value: string): string {
  return value.replace(/[^A-Za-z0-9_-]+/g, "-");
}

function defaultStorage(): HelpStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Load the guide JSON from the page's script element for `app`, or null. */
export function loadGuide(app: string, doc: Document = document): HelpGuide | null {
  const script = doc.getElementById(`${SCRIPT_ID_PREFIX}${slug(app)}`);
  if (!script || !script.textContent) return null;
  try {
    const data = JSON.parse(script.textContent) as HelpGuide;
    if (!data || !Array.isArray(data.steps)) return null;
    return data;
  } catch {
    return null;
  }
}

export class AppHelp {
  readonly root: HTMLElement;
  readonly app: string;
  readonly guide: HelpGuide;
  readonly language: string;
  private readonly storage: HelpStorage | null;
  private readonly steps: HelpStep[];
  private readonly tourSteps: HelpStep[];

  private button: HTMLButtonElement;
  private panel: HTMLElement | null = null;
  private tour: HTMLElement | null = null;
  private highlight: HTMLElement | null = null;
  private tourIndex = 0;

  constructor(root: HTMLElement, options: AppHelpOptions = {}) {
    this.root = root;
    this.app = options.app || root.getAttribute(HELP_ATTRIBUTE) || "default";
    this.language = options.language || activeLanguage();
    this.storage = options.storage === undefined ? defaultStorage() : options.storage;
    this.guide = loadGuide(this.app) ?? { app: this.app, steps: [] };
    this.steps = this.guide.steps;
    this.tourSteps = this.steps.filter((s) => typeof s.target === "string" && s.target !== "");

    root.classList.add(CLS);
    this.button = this.renderButton();
    root.appendChild(this.button);

    if (options.autoStart === false) return;
    if (!this.firstOpenDone() && this.tourSteps.length > 0) {
      // Defer so the targets exist in the DOM by the time the tour highlights.
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(() => this.startTour());
      } else {
        this.startTour();
      }
    }
  }

  get open(): boolean {
    return this.panel !== null;
  }

  /** True once the user has completed or dismissed the first-open tour. */
  firstOpenDone(): boolean {
    try {
      return this.storage?.getItem(`${STORAGE_PREFIX}${this.app}:done`) === "1";
    } catch {
      return true;
    }
  }

  private markFirstOpenDone(): void {
    try {
      this.storage?.setItem(`${STORAGE_PREFIX}${this.app}:done`, "1");
    } catch {
      // Private mode / full quota: the guide still works, it just re-runs next open.
    }
  }

  /** Open the `?` help panel. */
  openPanel(): void {
    if (this.panel) return;
    this.closeTour();
    this.panel = this.renderPanel();
    this.root.appendChild(this.panel);
    this.emit({ view: "panel" });
    const closeBtn = this.panel.querySelector<HTMLButtonElement>(`.${CLS_CLOSE}`);
    closeBtn?.focus();
  }

  closePanel(): void {
    if (!this.panel) return;
    this.panel.remove();
    this.panel = null;
    this.emit({ view: "closed" });
  }

  /** Open or close the panel (the `?` button behavior). */
  toggle(): void {
    if (this.panel) this.closePanel();
    else this.openPanel();
  }

  /** Start the first-open coach-mark tour from the beginning. */
  startTour(): void {
    if (this.tourSteps.length === 0) return;
    this.closePanel();
    this.tourIndex = 0;
    if (!this.tour) {
      this.tour = this.renderTour();
      this.root.appendChild(this.tour);
    }
    this.showTourStep(0);
    this.emit({ view: "tour", step: 0 });
  }

  /** Replay the tour (available from the panel footer). */
  replayTour(): void {
    this.startTour();
  }

  closeTour(): void {
    if (!this.tour) return;
    this.tour.remove();
    this.tour = null;
    this.highlight?.remove();
    this.highlight = null;
    this.markFirstOpenDone();
    this.emit({ view: "closed" });
  }

  nextTourStep(): void {
    if (this.tourIndex < this.tourSteps.length - 1) {
      this.showTourStep(this.tourIndex + 1);
      this.emit({ view: "tour", step: this.tourIndex });
    } else {
      this.closeTour();
    }
  }

  prevTourStep(): void {
    if (this.tourIndex > 0) {
      this.showTourStep(this.tourIndex - 1);
      this.emit({ view: "tour", step: this.tourIndex });
    }
  }

  private showTourStep(index: number): void {
    this.tourIndex = index;
    const step = this.tourSteps[index];
    if (!this.tour) return;
    // Highlight the target if it exists on the page.
    const target = step.target ? document.querySelector(step.target) : null;
    if (this.highlight) this.highlight.remove();
    if (target) {
      this.highlight = document.createElement("div");
      this.highlight.className = CLS_TOUR_HIGHLIGHT;
      const rect = target.getBoundingClientRect();
      Object.assign(this.highlight.style, {
        position: "fixed",
        left: `${rect.left - 4}px`,
        top: `${rect.top - 4}px`,
        width: `${rect.width + 8}px`,
        height: `${rect.height + 8}px`,
      });
      this.root.appendChild(this.highlight);
    }
    const bubble = this.tour.querySelector(`.${CLS_TOUR_BUBBLE}`);
    if (bubble) {
      const icon = step.icon ? `<span class="${CLS_STEP_ICON}" aria-hidden="true">${step.icon}</span>` : "";
      const title = stepText(step.title, this.language) || gettext("Guide");
      const body = stepText(step.body, this.language);
      bubble.innerHTML =
        `<div class="${CLS_STEP}">` +
        `${icon}<div class="${CLS_STEP_TITLE}">${title}</div>` +
        (body ? `<div class="${CLS_STEP_BODY}">${body}</div>` : "") +
        `</div>`;
    }
    const count = this.tour.querySelector(`.${CLS_COUNT}`);
    if (count) count.textContent = `${index + 1} / ${this.tourSteps.length}`;
    const nav = this.tour.querySelector(`.${CLS_NAV}`);
    if (nav) {
      const prev = nav.querySelector('[data-act="prev"]') as HTMLButtonElement | null;
      if (prev) prev.disabled = index === 0;
      const next = nav.querySelector('[data-act="next"]') as HTMLButtonElement | null;
      if (next) next.textContent = index === this.tourSteps.length - 1 ? gettext("Done") : gettext("Next");
    }
  }

  private renderButton(): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button";
    button.className = CLS_BUTTON;
    button.setAttribute("aria-label", gettext("How to use"));
    button.setAttribute("data-stx-help-open", "");
    button.textContent = "?";
    button.addEventListener("click", () => this.toggle());
    return button;
  }

  private renderPanel(): HTMLElement {
    const panel = document.createElement("div");
    panel.className = CLS_PANEL;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", gettext("How to use"));

    const header = document.createElement("div");
    header.className = `${CLS}__header`;
    const title = document.createElement("h3");
    title.className = `${CLS}__title`;
    title.textContent = gettext("How to use");
    const close = document.createElement("button");
    close.type = "button";
    close.className = CLS_CLOSE;
    close.setAttribute("aria-label", gettext("Close"));
    close.textContent = "\u00d7";
    close.addEventListener("click", () => this.closePanel());
    header.append(title, close);
    panel.appendChild(header);

    const body = document.createElement("div");
    body.className = CLS_PANEL_BODY;
    this.steps.forEach((step, i) => {
      const item = document.createElement("div");
      item.className = CLS_STEP;
      const icon = step.icon ? `<span class="${CLS_STEP_ICON}" aria-hidden="true">${step.icon}</span>` : "";
      const num = `<span class="${CLS}__step-num" aria-hidden="true">${i + 1}</span>`;
      const title = stepText(step.title, this.language);
      const bodyText = stepText(step.body, this.language);
      item.innerHTML =
        `${num}${icon}<div class="${CLS}__step-text">` +
        (title ? `<div class="${CLS_STEP_TITLE}">${title}</div>` : "") +
        (bodyText ? `<div class="${CLS_STEP_BODY}">${bodyText}</div>` : "") +
        `</div>`;
      body.appendChild(item);
    });
    panel.appendChild(body);

    const footer = document.createElement("div");
    footer.className = `${CLS}__footer`;
    const replay = document.createElement("button");
    replay.type = "button";
    replay.className = `${CLS}__replay`;
    replay.textContent = gettext("Replay the tour");
    replay.addEventListener("click", () => this.replayTour());
    footer.appendChild(replay);
    panel.appendChild(footer);

    // Escape closes the panel.
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        this.closePanel();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return panel;
  }

  private renderTour(): HTMLElement {
    const tour = document.createElement("div");
    tour.className = CLS_TOUR;
    tour.setAttribute("role", "dialog");
    tour.setAttribute("aria-modal", "true");
    tour.setAttribute("aria-label", gettext("How to use"));

    const bubble = document.createElement("div");
    bubble.className = CLS_TOUR_BUBBLE;
    tour.appendChild(bubble);

    const meta = document.createElement("div");
    meta.className = `${CLS}__tour-meta`;
    const count = document.createElement("span");
    count.className = CLS_COUNT;
    const nav = document.createElement("div");
    nav.className = CLS_NAV;
    const prev = document.createElement("button");
    prev.type = "button";
    prev.dataset.act = "prev";
    prev.textContent = gettext("Back");
    const next = document.createElement("button");
    next.type = "button";
    next.dataset.act = "next";
    next.textContent = gettext("Next");
    const skip = document.createElement("button");
    skip.type = "button";
    skip.dataset.act = "skip";
    skip.textContent = gettext("Skip");
    nav.append(prev, next, skip);
    meta.append(count, nav);
    tour.appendChild(meta);

    prev.addEventListener("click", () => this.prevTourStep());
    next.addEventListener("click", () => this.nextTourStep());
    skip.addEventListener("click", () => this.closeTour());

    return tour;
  }

  private emit(detail: Omit<HelpChangeDetail, "app"> & { app?: string }): void {
    const full: HelpChangeDetail = { app: this.app, ...detail };
    this.root.dispatchEvent(new CustomEvent(HELP_CHANGE, { detail: full, bubbles: true }));
  }

  /** Remove all rendered help chrome (SPA teardown). */
  destroy(): void {
    this.panel?.remove();
    this.tour?.remove();
    this.highlight?.remove();
    this.panel = null;
    this.tour = null;
    this.highlight = null;
  }
}
