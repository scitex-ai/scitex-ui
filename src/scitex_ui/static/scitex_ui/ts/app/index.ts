/**
 * App components — reusable feature UI (file browser, docs sidebar).
 */
export {
  renderImageAttachment,
  renderFileAttachment,
} from "./attachment";
export type {
  ImageAttachmentConfig,
  FileAttachmentConfig,
} from "./attachment";

export { FileBrowser } from "./file-browser";
export type { FileNode, FileBrowserConfig } from "./file-browser";

export { PackageDocsSidebar } from "./package-docs-sidebar";
export type {
  PackageInfo,
  PackageDocsSidebarConfig,
} from "./package-docs-sidebar";
