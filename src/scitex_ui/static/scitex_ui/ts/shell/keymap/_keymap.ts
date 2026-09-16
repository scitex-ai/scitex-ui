/**
 * The Keymap — Emacs major-mode semantics over the Command Registry.
 *
 * A GLOBAL keymap is always active. An active page/app MODE adds a mode keymap
 * on top: bindings are resolved mode-first, so a mode can shadow a global
 * chord (e.g. an editor mode rebinding C-c) without touching the global map.
 * Activating a mode is what makes mode-scoped commands in the registry active.
 *
 * KEYBOARD-FIRST, NOT MOUSE-ONLY. Every command reaches the same action a
 * button would, through `Keymap.dispatchSequence` — the keyboard IS the
 * primary interface, the button is an alternative caller of the same command.
 *
 * INPUT/CONTENTEDITABLE SUPPRESSION. A keydown inside a text field, textarea,
 * select, or [contenteditable] does NOT fire command chords UNLESS the binding
 * opted in (a binding's `inInput: true`). This is the default that keeps C-c
 * from eating a copy in an editor; an app opts a specific binding in when it
 * genuinely wants it there (e.g. a terminal that captures everything).
 *
 * CONFLICT DETECTION is at bind time, not keypress time: binding the same
 * chord to two commands in the same scope is reported immediately so the
 * authoring app sees it, rather than the user hitting a silent one-wins.
 */

import {
  type Chord,
  type Sequence,
  parseChord,
  parseSequence,
  sequenceKey,
  eventToChord,
  chordMatches,
} from "./_chords";
import { CommandRegistry, globalRegistry } from "./_registry";

/** A single chord-to-command binding. */
export interface Binding {
  /** The sequence, e.g. "C-x C-s" or "C-c". Stored canonical. */
  sequence: Sequence;
  /** The command ID to run when the sequence completes. */
  commandId: string;
  /** When true, the binding fires even inside input/contenteditable. */
  inInput?: boolean;
}

export type BindingScope = "global" | string; // string = a mode name

export interface Conflict {
  sequenceKey: string;
  scope: BindingScope;
  existingCommandId: string;
  newCommandId: string;
}

export interface KeymapOptions {
  registry?: CommandRegistry;
  /** Storage for user overrides; defaults to an in-memory map (no persistence
   *  — persistence is the consuming app's concern, passed in). */
  overrideStorage?: Map<string, Sequence>;
}

const INPUT_SELECTOR =
  "input, textarea, select, [contenteditable=''], [contenteditable='true'], [contenteditable='plaintext-only']";

export class Keymap {
  private readonly registry: CommandRegistry;
  /** scope -> list of bindings. "global" is always present. */
  private readonly bindings = new Map<BindingScope, Binding[]>();
  /** scope -> canonical-sequence-key -> commandId, for O(1) resolution + conflicts. */
  private readonly index = new Map<BindingScope, Map<string, string>>();
  private readonly overrideStorage: Map<string, Sequence>;
  /** Pending prefix sequence while a multi-chord command is being typed. */
  private pending: Sequence = [];
  // Typed as Event (not KeyboardEvent) so it satisfies addEventListener's
  // EventListener signature; handleKeydown duck-types the keyboard fields.
  private readonly onKeydown: (event: Event) => void;

  constructor(options: KeymapOptions = {}) {
    this.registry = options.registry ?? globalRegistry;
    this.overrideStorage = options.overrideStorage ?? new Map();
    this.bindings.set("global", []);
    this.index.set("global", new Map());
    this.onKeydown = (event) => this.handleKeydown(event);
  }

  get currentMode(): string | null {
    return this.registry.currentMode;
  }

  /** Activate a page/app mode. Installs the scope so it is bindable, and
   *  tells the registry which mode-scoped commands are now live. */
  activateMode(mode: string): void {
    if (!this.bindings.has(mode)) {
      this.bindings.set(mode, []);
      this.index.set(mode, new Map());
    }
    this.registry.setMode(mode);
    this.resetPending();
  }

  /** Return to global-only. Mode-scoped commands go inactive. */
  deactivateMode(): void {
    this.registry.setMode(null);
    this.resetPending();
  }

  /** Bind a chord (or "C-x C-s" sequence) to a command ID in a scope.
   *  Returns a Conflict when the chord was already bound to a DIFFERENT
   *  command in that scope — the authoring app decides what to do. Re-binding
   *  the same chord to the same command is a no-op, not a conflict. */
  bind(scope: BindingScope, sequenceStr: string, commandId: string, inInput = false): Conflict | null {
    if (scope !== "global") {
      if (!this.bindings.has(scope)) {
        this.bindings.set(scope, []);
        this.index.set(scope, new Map());
      }
    }
    const seq = parseSequence(sequenceStr);
    const key = sequenceKey(seq);
    const scopeIndex = this.index.get(scope)!;
    const existing = scopeIndex.get(key);
    if (existing !== undefined && existing !== commandId) {
      return { sequenceKey: key, scope, existingCommandId: existing, newCommandId: commandId };
    }
    if (existing === commandId) return null; // idempotent re-bind
    scopeIndex.set(key, commandId);
    this.bindings.get(scope)!.push({ sequence: seq, commandId, inInput });
    return null;
  }

  /** All bindings a user has overridden this chord to, as a fresh map. */
  private effectiveScope(): BindingScope {
    return this.currentMode ?? "global";
  }

  /**
   * Apply a user override: remember that `sequenceStr` now runs `commandId`
   * instead of its default. Overrides are stored in `overrideStorage` keyed by
   * command ID and consulted during resolution. This is the "user override
   * overlay" — the app persists overrideStorage as it sees fit.
   */
  setOverride(commandId: string, sequenceStr: string): void {
    this.overrideStorage.set(commandId, parseSequence(sequenceStr));
  }

  unbind(commandId: string): void {
    for (const [scope, list] of this.bindings) {
      const kept = list.filter((b) => b.commandId !== commandId);
      this.bindings.set(scope, kept);
      // rebuild the index for this scope
      const newIndex = new Map<string, string>();
      for (const b of kept) newIndex.set(sequenceKey(b.sequence), b.commandId);
      this.index.set(scope, newIndex);
    }
    this.overrideStorage.delete(commandId);
  }

  /** Reset every user override; default bindings remain. */
  resetOverrides(): void {
    this.overrideStorage.clear();
  }

  /**
   * Resolve a completed chord sequence to a command ID, walking scope priority:
   * the active mode first, then global. Returns null when nothing is bound.
   */
  resolve(sequence: Sequence): { commandId: string; scope: BindingScope } | null {
    const key = sequenceKey(sequence);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const id = this.index.get(scope)?.get(key);
      if (id !== undefined) return { commandId: id, scope };
    }
    return null;
  }

  /** Whether the in-progress `pending` sequence is a prefix of any binding in
   *  the effective scope chain — keeps a multi-chord command alive while the
   *  user types it, and expires it the moment no binding could complete. */
  private isPendingViable(): boolean {
    const key = sequenceKey(this.pending);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const scopeIndex = this.index.get(scope);
      if (!scopeIndex) continue;
      for (const bound of scopeIndex.keys()) {
        if (bound === key || bound.startsWith(key + " ")) return true;
      }
    }
    return false;
  }

  private inInputElement(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    return target.closest(INPUT_SELECTOR) !== null;
  }

  private findBindingByChord(sequence: Sequence): { binding: Binding; scope: BindingScope } | null {
    const key = sequenceKey(sequence);
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      const binding = list.find((b) => sequenceKey(b.sequence) === key);
      if (binding) return { binding, scope };
    }
    return null;
  }

  private handleKeydown(event: Event): void {
    // `as KeyboardEvent` is a type assertion (no runtime cost). The fields are
    // present on any real keydown event; harnesses (vitest/jsdom) that pass
    // plain objects still satisfy the read.
    const ev = event as KeyboardEvent;
    const key = ev.key;
    const ctrlKey = ev.ctrlKey;
    const altKey = ev.altKey;
    const shiftKey = ev.shiftKey;
    const metaKey = ev.metaKey;
    if (typeof key !== "string") return;
    const preventDefault = () => ev.preventDefault();
    const target = ev.target ?? null;
    const chord: Chord | null = eventToChord({ key, ctrlKey, altKey, shiftKey, metaKey });
    if (chord === null) return;

    // Suppression: inside an input, only bindings that opted in fire. A bare
    // modifier or a non-optimised chord inside input is passed through.
    if (this.inInputElement(target)) {
      const probe = this.findBindingByChord([...this.pending, chord]);
      if (!probe || !probe.binding.inInput) {
        this.resetPending();
        return;
      }
    }

    this.pending = [...this.pending, chord];

    const hit = this.findBindingByChord(this.pending);
    if (hit && sequenceKey(hit.binding.sequence) === sequenceKey(this.pending)) {
      // Exact match: dispatch the command. Conditional consumption — swallow
      // the key ONLY when the command actually consumed it (ran AND its action
      // didn't report a no-op). A no-op (e.g. "delete" with nothing selected)
      // returns false, so we do NOT preventDefault and the key's native
      // browser behavior is preserved. See CommandDef.action.
      const consumed = this.registry.run(hit.binding.commandId, { via: "keyboard", source: target }, undefined);
      if (consumed) preventDefault();
      this.resetPending();
      return;
    }

    if (this.isPendingViable()) {
      // A real prefix — swallow the key so it doesn't also type into the page.
      preventDefault();
      return;
    }

    // Dead end: no binding can complete from here. Expire and let the key do
    // whatever the page would have done with it.
    this.resetPending();
  }

  /** Programmatic dispatch of a full sequence (agent / button path converges
   *  here too). Returns the command ID run, or null. */
  dispatchSequence(sequenceStr: string, via: "button" | "agent" | "program" = "program"): string | null {
    const seq = parseSequence(sequenceStr);
    const hit = this.resolve(seq);
    if (!hit) return null;
    const ok = this.registry.run(hit.commandId, { via });
    return ok ? hit.commandId : null;
  }

  private resetPending(): void {
    this.pending = [];
  }

  /** Attach the keydown listener. Returns a detach function — the lifecycle
   *  cleanup for SPA navigation. Callers (the shell or an app) hold the
   *  returned function and call it on teardown. */
  attach(target: EventTarget = document): () => void {
    target.addEventListener("keydown", this.onKeydown, true);
    return () => target.removeEventListener("keydown", this.onKeydown, true);
  }

  /** The introspection model: current mode + every command with the chords
   *  bound to it (resolved across scopes). Feeds the help UI and agent tools. */
  help(): {
    mode: string | null;
    commands: Array<{
      id: string;
      label: string;
      group?: string;
      active: boolean;
      chords: string[];
    }>;
  } {
    // map commandId -> chord display strings, mode-first
    const byCommand = new Map<string, string[]>();
    const scopes: BindingScope[] =
      this.currentMode !== null ? [this.currentMode, "global"] : ["global"];
    for (const scope of scopes.reverse()) {
      const list = this.bindings.get(scope);
      if (!list) continue;
      for (const b of list) {
        const arr = byCommand.get(b.commandId) ?? [];
        arr.push(sequenceKey(b.sequence));
        byCommand.set(b.commandId, arr);
      }
    }
    return {
      mode: this.currentMode,
      commands: this.registry.list().map((c) => ({
        ...c,
        chords: byCommand.get(c.id) ?? [],
      })),
    };
  }
}

export { parseChord, chordMatches };
