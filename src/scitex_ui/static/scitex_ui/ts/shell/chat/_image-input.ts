/**
 * ImageInputManager — manages image attachments for AI chat.
 *
 * Ported from scitex-cloud's image-input.ts.
 * Features: file picker, clipboard paste, thumbnails, base64 export.
 */

interface Attachment {
  file: File;
  dataUrl: string;
  mime: string;
  thumbEl: HTMLElement;
}

const MAX_IMAGES = 4;
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

/**
 * A picker for pages that ship none.
 *
 * Kept out of the document flow rather than `display:none` — a hidden input is
 * still clickable programmatically, and `.click()` on a `display:none` element
 * is refused by some browsers.
 */
export function createHiddenFileInput(
  extraAttributes: Record<string, string> = {},
): HTMLInputElement {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.multiple = true;
  input.style.cssText =
    "position:absolute;width:1px;height:1px;opacity:0;pointer-events:none;";
  for (const [name, value] of Object.entries(extraAttributes)) {
    input.setAttribute(name, value);
  }
  document.body.appendChild(input);
  return input;
}

export class ImageInputManager {
  private previewEl: HTMLElement;
  private fileInput: HTMLInputElement;
  private attachments: Attachment[] = [];

  /**
   * @param fileInput  The page's own picker. Omit it and one is synthesised —
   *   a template that ships no `<input type="file">` should lose the paperclip
   *   button, not the whole image feature. The caller cannot supply what its
   *   template does not have, and requiring it pushed that decision to the
   *   wrong layer.
   */
  constructor(previewEl: HTMLElement, fileInput?: HTMLInputElement | null) {
    this.previewEl = previewEl;
    this.fileInput = fileInput ?? createHiddenFileInput();
    this.fileInput.addEventListener("change", () => this.onFilesSelected());
  }

  /** Bind clipboard paste on a textarea. */
  bindPaste(textarea: HTMLTextAreaElement): void {
    textarea.addEventListener("paste", (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) this.addFile(file);
        }
      }
    });
  }

  /**
   * Take files from a picker this manager does not own.
   *
   * WebcamCapture synthesises its own `capture="environment"` input when the
   * page ships none, and nothing would consume its `change` event otherwise —
   * the manager only listens to the picker it was given.
   */
  addFiles(files: Iterable<File>): void {
    for (const file of files) this.addFile(file);
  }

  /** Add image from a data URL (used by sketch canvas). */
  addImageFromDataUrl(dataUrl: string, mime: string): void {
    if (this.attachments.length >= MAX_IMAGES) return;
    const byteStr = atob(dataUrl.split(",")[1]);
    const ab = new ArrayBuffer(byteStr.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteStr.length; i++) ia[i] = byteStr.charCodeAt(i);
    const file = new File([ab], "sketch.png", { type: mime });
    this.addAttachment(file, dataUrl, mime);
  }

  hasAttachments(): boolean {
    return this.attachments.length > 0;
  }

  getAttachmentsAsBase64(): { mime: string; base64: string }[] {
    return this.attachments.map((a) => ({
      mime: a.mime,
      base64: a.dataUrl.split(",")[1],
    }));
  }

  clearAttachments(): void {
    this.attachments = [];
    this.previewEl.innerHTML = "";
  }

  /** Render small inline thumbnails inside a user message bubble. */
  renderInlineThumbsInto(container: HTMLElement): void {
    if (this.attachments.length === 0) return;
    const strip = document.createElement("div");
    strip.className = "stx-shell-ai-msg-thumbs";
    for (const a of this.attachments) {
      const img = document.createElement("img");
      img.src = a.dataUrl;
      img.className = "stx-shell-ai-msg-thumb";
      strip.appendChild(img);
    }
    container.appendChild(strip);
  }

  private onFilesSelected(): void {
    const files = this.fileInput.files;
    if (!files) return;
    for (const file of Array.from(files)) this.addFile(file);
    this.fileInput.value = "";
  }

  private addFile(file: File): void {
    if (this.attachments.length >= MAX_IMAGES) return;
    if (file.size > MAX_SIZE_BYTES) return;
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      this.addAttachment(file, dataUrl, file.type);
    };
    reader.readAsDataURL(file);
  }

  private addAttachment(file: File, dataUrl: string, mime: string): void {
    const thumb = document.createElement("div");
    thumb.className = "stx-shell-ai-image-thumb";

    const img = document.createElement("img");
    img.src = dataUrl;
    thumb.appendChild(img);

    const removeBtn = document.createElement("button");
    removeBtn.className = "stx-shell-ai-image-thumb-remove";
    removeBtn.innerHTML = "&times;";
    const att: Attachment = { file, dataUrl, mime, thumbEl: thumb };
    removeBtn.addEventListener("click", () => this.removeAttachment(att));
    thumb.appendChild(removeBtn);

    this.previewEl.appendChild(thumb);
    this.attachments.push(att);
  }

  private removeAttachment(att: Attachment): void {
    const idx = this.attachments.indexOf(att);
    if (idx >= 0) this.attachments.splice(idx, 1);
    att.thumbEl.remove();
  }
}
