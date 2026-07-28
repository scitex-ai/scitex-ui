/**
 * App components — reusable feature UI (file browser, docs sidebar).
 */
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
