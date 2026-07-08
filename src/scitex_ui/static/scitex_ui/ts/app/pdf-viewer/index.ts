/**
 * @scitex/ui/pdf-viewer — L1 neutral PDF viewer (ADR 0001).
 *
 * Framework-neutral vanilla-TS renderer + always-on minimal pen UI
 * (Pointer Events → Wacom / iPad / finger), exported as the named subpath
 * `@scitex/ui/pdf-viewer` so it is reachable WITHOUT the app/shell bundle.
 *
 * IMPORTANT — import must stay INERT: no shell import, no DOM work, no
 * side effects at module load. hub imports this from both workspace-shell
 * and standalone-app contexts; construction happens only via
 * `createPdfViewer()`.
 *
 * Status: interface-first stub. The hook + controlled-mark-state API is
 * functional now (consumers can wire the full event/feed flow); PDF.js
 * page rendering + screen↔PDF-space projection land next (marked TODO).
 */

import type {
  Mark,
  PdfCoords,
  PdfPalette,
  PdfSource,
  PdfTool,
  PdfViewerApi,
  PdfViewerHooks,
  PdfViewerOptions,
} from "./types";

export * from "./types";

/** Construct an L1 viewer bound to `options.container`. */
export function createPdfViewer(options: PdfViewerOptions): PdfViewerApi {
  return new PdfViewer(options);
}

function applyPalette(el: HTMLElement, palette: PdfPalette): void {
  for (const [key, value] of Object.entries(palette)) {
    el.style.setProperty(`--stx-verdict-${key}`, value);
  }
}

class PdfViewer implements PdfViewerApi {
  private readonly container: HTMLElement;
  private readonly hooks: PdfViewerHooks;
  private marks: Mark[] = [];
  private tool: PdfTool;
  private src?: PdfSource;

  constructor(options: PdfViewerOptions) {
    this.container = options.container;
    this.hooks = options.hooks ?? {};
    this.tool = options.tool ?? "highlight";
    this.src = options.src;
    if (options.palette) {
      applyPalette(this.container, options.palette);
    }
    // No rendering on construct beyond palette wiring; load() drives render.
  }

  async load(src: PdfSource): Promise<void> {
    this.src = src;
    // TODO(pdf.js): resolve pdfjs-dist lazily, render pages into container,
    // then emit onPageRender(page, viewport) per rendered page.
  }

  getCoords(_clientX: number, _clientY: number): PdfCoords | null {
    // TODO(pdf.js): hit-test against rendered page canvases and invert the
    // page viewport transform to zoom-invariant PDF-space. Null until render.
    return null;
  }

  setTool(tool: PdfTool): void {
    this.tool = tool;
  }

  setMarks(marks: Mark[]): void {
    this.marks = marks.map((m) => ({ ...m }));
    this.hooks.onMarksChange?.(this.getMarks());
    // TODO(pdf.js): repaint the overlay layer from this.marks.
  }

  getMarks(): Mark[] {
    return this.marks.map((m) => ({ ...m }));
  }

  setPalette(palette: PdfPalette): void {
    applyPalette(this.container, palette);
  }

  destroy(): void {
    // TODO(pdf.js): remove Pointer Event listeners + detach canvases.
    this.marks = [];
  }
}
