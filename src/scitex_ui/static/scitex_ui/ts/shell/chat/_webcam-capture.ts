/**
 * WebcamCapture — live camera feed with snapshot for AI chat.
 *
 * Ported from scitex-cloud's webcam-capture.ts.
 * Opens modal overlay with getUserMedia, capture button, camera flip.
 * Falls back to file picker if camera denied.
 */

import type { ImageInputManager } from "./_image-input";
import { createHiddenFileInput } from "./_image-input";

export class WebcamCapture {
  private overlay: HTMLElement | null = null;
  private video: HTMLVideoElement | null = null;
  private stream: MediaStream | null = null;
  private imageInput: ImageInputManager;
  private fileInput: HTMLInputElement;

  /**
   * @param fileInput  Used when getUserMedia is refused. Omit it and one is
   *   synthesised carrying `capture="environment"`.
   *
   *   That attribute is the whole point of the fallback: on a phone it opens
   *   the CAMERA, which is what the user asked for by pressing a camera
   *   button. Without it they get a file browser — technically a fallback,
   *   but not to the thing they wanted. A caller-supplied input is used
   *   as-is and never mutated: it is usually the page's general "attach a
   *   file" picker, and forcing `capture` onto it would take away the
   *   ability to choose an existing photo.
   */
  constructor(
    imageInput: ImageInputManager,
    fileInput?: HTMLInputElement | null,
  ) {
    this.imageInput = imageInput;
    if (fileInput) {
      // The manager already listens to the page's own picker; binding here too
      // would add every chosen photo twice.
      this.fileInput = fileInput;
    } else {
      this.fileInput = createHiddenFileInput({ capture: "environment" });
      this.fileInput.addEventListener("change", () => {
        const files = this.fileInput.files;
        if (files) this.imageInput.addFiles(Array.from(files));
        this.fileInput.value = "";
      });
    }
  }

  async open(): Promise<void> {
    if (this.overlay) return;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 } },
        audio: false,
      });
    } catch {
      this.fileInput.click();
      return;
    }

    this.overlay = this.buildUI();
    document.body.appendChild(this.overlay);
    this.video!.srcObject = this.stream;
  }

  close(): void {
    this.stopStream();
    this.overlay?.remove();
    this.overlay = null;
    this.video = null;
  }

  private buildUI(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "stx-shell-webcam-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:10000;display:flex;align-items:center;justify-content:center;";

    const panel = document.createElement("div");
    panel.className = "stx-shell-webcam-panel";
    panel.style.cssText =
      "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px;background:var(--bg-secondary,#161b22);border-radius:8px;";
    overlay.appendChild(panel);

    this.video = document.createElement("video");
    this.video.autoplay = true;
    this.video.playsInline = true;
    this.video.muted = true;
    this.video.style.cssText =
      "max-width:640px;max-height:480px;border-radius:4px;";
    panel.appendChild(this.video);

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:12px;";

    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    cancelBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;";
    cancelBtn.addEventListener("click", () => this.close());

    const captureBtn = document.createElement("button");
    captureBtn.innerHTML = '<i class="fas fa-circle"></i> Capture';
    captureBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:none;background:#ef4444;color:#fff;cursor:pointer;font-size:16px;";
    captureBtn.addEventListener("click", () => this.capture());

    const flipBtn = document.createElement("button");
    flipBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Flip';
    flipBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;";
    flipBtn.addEventListener("click", () => this.switchCamera());

    actions.append(cancelBtn, captureBtn, flipBtn);
    panel.appendChild(actions);

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.close();
    });

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.close();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return overlay;
  }

  private capture(): void {
    if (!this.video) return;
    const canvas = document.createElement("canvas");
    canvas.width = this.video.videoWidth || 640;
    canvas.height = this.video.videoHeight || 480;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    this.imageInput.addImageFromDataUrl(dataUrl, "image/jpeg");
    this.close();
  }

  private async switchCamera(): Promise<void> {
    if (!this.stream || !this.video) return;
    const currentTrack = this.stream.getVideoTracks()[0];
    const currentFacing =
      currentTrack.getSettings().facingMode || "environment";
    const newFacing = currentFacing === "environment" ? "user" : "environment";

    // Flipping is destructive: the old stream must be released before the new
    // one is acquired, because a device with a single camera cannot serve both
    // at once. So a failed acquire leaves us with nothing, and "ignore the
    // error" would strand the modal on a dead preview — stream null, srcObject
    // holding stopped tracks, and the `!this.stream` guard above turning every
    // later Flip into a no-op. On a one-camera desktop that is every Flip.
    this.stopStream();
    if (await this.acquire(newFacing)) return;

    // The new facing is unavailable — the common, boring case. Put back what
    // the user had rather than leaving the session dead.
    if (await this.acquire(currentFacing)) return;

    // Both directions failed: the camera is genuinely gone (unplugged, or
    // claimed by another application). Close instead of presenting a black
    // rectangle that only Cancel can dismiss.
    this.close();
  }

  /** Acquire `facingMode` and attach it. Returns false if unavailable. */
  private async acquire(facingMode: string): Promise<boolean> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 } },
        audio: false,
      });
    } catch {
      this.stream = null;
      return false;
    }
    if (this.video) this.video.srcObject = this.stream;
    return true;
  }

  private stopStream(): void {
    if (this.stream) {
      for (const track of this.stream.getTracks()) track.stop();
      this.stream = null;
    }
  }
}
