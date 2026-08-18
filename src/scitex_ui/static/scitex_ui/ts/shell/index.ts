/**
 * Shell components — complete workspace shell framework.
 *
 * High-level entry point:
 *   import { initShell } from "scitex-ui/ts/shell";
 *   await initShell({ fileTree: {...}, terminal: {...}, ... });
 */

// Shell orchestrator
export { initShell } from "./_shell-init";
export type { ShellInstances } from "./_shell-init";
export type { ShellConfig } from "./types";
export { ThemeProvider } from "./theme-provider";
export type { Theme, ThemeProviderConfig } from "./theme-provider";

export { AppShell, Sidebar } from "./app-shell";
export type { AppShellConfig } from "./app-shell";

export { StatusBar } from "./status-bar";
export type {
  StatusBarConfig,
  StatusBarSection,
  StatusItem,
} from "./status-bar";

export { ShellFileTree } from "./file-tree";
export type { FileTreeAdapter, ShellFileTreeConfig } from "./file-tree";

export { ToolbarManager, KeyboardShortcuts } from "./toolbar";
export type {
  ToolbarCommand,
  CommandEventDetail,
  ButtonBinding,
  KeyShortcut,
  ToolbarConfig,
} from "./toolbar";

export { initTerminal, loadXtermModules, loadXtermCSS } from "./terminal";
export type {
  TerminalInstance,
  TerminalConnectionAdapter,
  TerminalConfig,
} from "./terminal";

export {
  processStream,
  renderMarkdown,
  saveMessage,
  loadMessages,
  clearMessages,
  loadHistory,
  pushHistory,
  appendToolTags,
  setModelBadge,
} from "./chat";
export type {
  ChatAdapter,
  AiContext,
  StoredMessage,
  StreamContext,
  ChatConfig,
} from "./chat";

export {
  ViewerManager,
  renderImageViewer,
  renderPdfViewer,
  detectFileType,
} from "./viewer";
export type { ViewerAdapter, ViewerConfig, OpenFile, FileType } from "./viewer";

export {
  initKeyboardShortcuts,
  showShortcutsModal,
  toggleShortcutsModal,
  registerShortcuts,
  setContextDetector,
} from "./keyboard-shortcuts";
export type {
  ShortcutContext,
  ShortcutDef,
  ShortcutSection,
} from "./keyboard-shortcuts";

export { initRepoMonitor, initMonitorToggle } from "./repo-monitor";
export type {
  RepoMonitorAdapter,
  RepoMonitorConfig,
  RecentFileEntry,
} from "./repo-monitor";

// Unified Resizer system (PointerEvent-based, with cascade and snap)
export {
  Resizer,
  BaseResizer,
  HorizontalResizer,
  VerticalResizer,
  autoInit as autoInitResizers,
  initNewResizers,
  magneticSnap,
  percentSnapPoints,
} from "./resizer";
export type {
  ResizerConfig,
  ResizerDirection,
  HorizontalConfig,
  VerticalConfig,
  BaseOpts,
  PropagationTarget,
} from "./resizer";

// Workspace Panel Resizer (legacy, used by data-panel-resizer attributes)
export {
  WorkspacePanelResizer,
  workspacePanelResizer,
  autoInitPanels,
  initNewPanels,
} from "./workspace-panel-resizer";
export type { PanelConfig } from "./workspace-panel-resizer";
export type { AxisConfig } from "./workspace-panel-resizer";
export { detectAxis, getAxis } from "./workspace-panel-resizer";

// Mobile pane-collapse gestures. The shell already ships these to the browser
// via js/shell/mobile-swipe.js (see ADR 0002), so consumers of
// standalone_shell.html get them with no wiring. Re-exported for consumers that
// bundle the TypeScript themselves and want to control init order.
export { init as initMobileSwipe } from "./mobile-swipe";
