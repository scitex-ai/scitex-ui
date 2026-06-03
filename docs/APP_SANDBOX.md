# SciTeX UI -- Frontend Isolation and App Sandbox

scitex-ui provides the shared component library and CSS architecture that keeps app styles isolated from the platform shell.

## CSS Architecture: Three Bundles

scitex-ui ships three CSS bundles with distinct scopes:

| Bundle       | File          | Scope | Contents |
|--------------|---------------|-------|----------|
| **shell.css** | `css/shell.css` | Platform chrome | Workspace layout, resizers, status bar, AI panel, theme, terminal, viewer |
| **app.css**   | `css/app.css`   | App content area | Data table, file browser, file tabs, selector nav, dropdowns, tooltips, media viewer |
| **all.css**   | `css/all.css`   | Combined | Imports both shell.css and app.css (convenience bundle) |

**Rule**: Shell CSS always wins. App CSS operates within the content area and cannot override shell layout, navigation, or chrome.

### CSS Loading Strategy

- **scitex-hub** loads `shell.css` in the base template -- always present
- **Apps** import `app.css` in their entry point TypeScript (e.g., `import "scitex-ui/css/app.css"`)
- Apps may also load their own CSS after `app.css` for app-specific styles

## `<AppSandbox>` Component (Planned)

A React component that wraps app content in a Shadow DOM boundary:

```tsx
<AppSandbox
  appName="figrecipe"
  theme={currentTheme}
  onEscapeAttempt={handleViolation}
>
  <FigrecipeEditor {...props} />
</AppSandbox>
```

### Responsibilities

1. **Shadow DOM encapsulation** -- app styles cannot leak into the shell
2. **Theme injection** -- platform theme variables passed via `:host` CSS custom properties
3. **DOM escape detection** -- MutationObserver watches for app elements appearing outside the shadow root
4. **Lifecycle management** -- clean mount/unmount with proper React root handling

### Theme Variable Contract

The shell exposes these CSS custom properties that apps can consume:

```css
:host {
  --stx-bg-primary: ...;
  --stx-bg-secondary: ...;
  --stx-text-primary: ...;
  --stx-text-secondary: ...;
  --stx-accent: ...;
  --stx-border: ...;
  --stx-radius: ...;
}
```

Apps read these variables instead of defining their own theme colors, ensuring visual consistency.

## `mountApp()` Interface

Generic function for mounting any app into a container:

```typescript
interface AppMountConfig {
  container: HTMLElement;
  appName: string;
  workingDir?: string;
  darkMode?: boolean;
  onEvent?: (event: string, data: unknown) => void;
}

function mountApp(config: AppMountConfig): { unmount: () => void };
```

Currently, each app implements its own mount function (e.g., `mountFigrecipeEditor()`). The generic `mountApp()` will unify this pattern.

## Shared React Components (App Layer)

Components available to all apps via `scitex-ui/react/app/`:

| Component | Purpose |
|-----------|---------|
| `DataTable` | Spreadsheet with selection, editing, virtual scroll, CSV import |
| `FileBrowser` | File tree with context menu, search, drag-and-drop |
| `FileTabs` | Tabbed file navigation |
| `MediaViewer` | Image/PDF/audio preview |
| `SelectorNav` | Horizontal tab/segment selector |
| `Dropdown` | Accessible dropdown menus |
| `ConfirmModal` | Confirmation dialogs |
| `Tooltip` | Hover tooltips |

## Shared React Components (Shell Layer)

Components used by the platform shell via `scitex-ui/react/shell/`:

| Component | Purpose |
|-----------|---------|
| `Workspace` | Three-column layout with resizable panels |
| `Chat` | AI chat interface |
| `Terminal` | xterm.js terminal integration |
| `Viewer` | Monaco editor + media viewer |
| `MediaInput` | Voice, webcam, sketch capture |

## TypeScript Components (Vanilla TS)

For non-React contexts, scitex-ui also provides class-based vanilla TS components under `ts/app/` and `ts/shell/` that mirror the React API:

- `DataTableManager` -- full spreadsheet (class-based)
- `FileBrowser` -- file tree (class-based)
- `Resizer` -- panel resize handles
- `AppShell` -- sidebar + content layout
- `ThemeProvider` -- theme switching

## DOM Escape Detection (Planned)

A `MutationObserver` on `document.body` that flags when an app inserts elements outside its sandbox:

```typescript
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node instanceof HTMLElement && !shadowRoot.contains(node)) {
        onEscapeAttempt(node);
      }
    }
  }
});
observer.observe(document.body, { childList: true, subtree: true });
```

## Key Files

| File | Purpose |
|------|---------|
| `css/shell.css` | Shell-level styles (imports shell/* partials) |
| `css/app.css` | App-level styles (imports app/* partials) |
| `css/all.css` | Combined bundle |
| `react/app/` | Shared React components for apps |
| `react/shell/` | Shell-level React components |
| `ts/app/` | Vanilla TS class-based components for apps |
| `ts/shell/` | Vanilla TS shell components |

## Cross-References

- **scitex-hub** (`docs/ARCHITECTURE/APP_PLATFORM.md`) -- Platform context injection, manifest loading, URL mounting
- **scitex-app** (`docs/APP_SDK.md`) -- Python-side `FilesBackend` protocol, path resolution
- **figrecipe** (`docs/SCITEX_APP_INTEGRATION.md`) -- Reference app using bridge init + fetch override pattern
