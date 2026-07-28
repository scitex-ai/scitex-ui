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

export { renderEmptyState } from "./empty";
export type { EmptyStateConfig } from "./empty";

export { FileBrowser } from "./file-browser";
export type { FileNode, FileBrowserConfig } from "./file-browser";

export { PackageDocsSidebar } from "./package-docs-sidebar";
export type {
  PackageInfo,
  PackageDocsSidebarConfig,
} from "./package-docs-sidebar";

export { ContextMenu, initContextMenu } from "./context-menu";
export type {
  ContextMenuConfig,
  ContextMenuEntry,
  ContextMenuItem,
  ContextMenuDivider,
  ContextMenuLabel,
} from "./context-menu";

export { Receipt, renderReceipt, RECEIPT_STATES } from "./receipt";
export type {
  ReceiptConfig,
  ReceiptGlyphs,
  ReceiptLabels,
  ReceiptState,
} from "./receipt";

export { ReplyQuote, renderReplyQuote } from "./reply-quote";
export type { ReplyQuoteConfig } from "./reply-quote";
