/**
 * The Command Registry — the single dispatch target for the keymap primitive.
 *
 * ONE command function. A command has a STABLE ID (the string every binding
 * and every consumer keys off), a human-readable LABEL (for the help UI), and
 * an ACTION. Button click, keyboard chord, and agent dispatch all resolve to
 * the same registered action — none of them calls app code directly. That
 * convergence is the operator's beta boundary: button, keyboard, and agent
 * dispatch converge on one command function.
 *
 * MACROS ARE FUTURE-ONLY. The registry deliberately leaves a clean caller
 * seam for them without implementing them: `runCommand` accepts an optional
 * `CallerInfo` that names WHO dispatched (keyboard / button / agent / program).
 * A future macro layer keys off that seam — a macro is just a caller that runs
 * a sequence of command IDs — so nothing here needs to change when macros
 * arrive. There is no macro field on a command, and no macro storage; inventing
 * either now would be the speculative surface the boundary rules out.
 *
 * THE REGISTRY IS A GLOBAL SINGLETON by default, but every function also takes
 * an explicit registry argument, so tests and multiple independent pages can
 * build private registries without leaking into each other. `globalRegistry`
 * is the one the runtime wires up.
 */

export interface CallerInfo {
  /** How this dispatch arrived. A future macro layer reads this. */
  via: "keyboard" | "button" | "agent" | "program";
  /** Optional originating element (button/agent), for debugging + a11y. */
  source?: EventTarget | null;
}

/** A registered command's definition. */
export interface CommandDef {
  /** Stable, unique ID — the contract consumers and bindings key off. */
  id: string;
  /** Human label for the help UI and agent introspection. */
  label: string;
  /** The action. Receives an optional dispatch payload from the caller. */
  action: (payload?: unknown) => void;
  /**
   * Optional: this command only makes sense in certain modes. When present,
   * the command is inactive (and unbindable-by-default) outside those modes.
   * Omitted = global, active in every mode.
   */
  modes?: ReadonlySet<string>;
  /** Optional group for the help UI's sectioning (e.g. "File", "View"). */
  group?: string;
}

/** Result of a lookup — lets callers distinguish "not found" from "found". */
export interface CommandHandle {
  def: CommandDef;
  /** True when the command is active in the current mode (global = always). */
  active: boolean;
}

export class CommandRegistry {
  private readonly commands = new Map<string, CommandDef>();
  /** The active page/app mode, or null when none is active (global only). */
  private mode: string | null = null;

  /** Register or REPLACE a command. Returns false when the ID is taken by a
   *  DIFFERENT definition (a re-registration with the same ID is allowed —
   *  it is how an app updates its own command without clearing the world). */
  set(def: CommandDef): boolean {
    const existing = this.commands.get(def.id);
    if (existing && existing !== def) {
      // Same ID, different definition: this is a real conflict the caller
      // should know about. We replace (latest wins) but report it.
      this.commands.set(def.id, def);
      return false;
    }
    this.commands.set(def.id, def);
    return true;
  }

  /** Unregister by ID. Returns true if something was removed. */
  unset(id: string): boolean {
    return this.commands.delete(id);
  }

  /** True if a command with this ID is registered (regardless of mode). */
  has(id: string): boolean {
    return this.commands.has(id);
  }

  /** Look up a command, reporting whether it is active in the current mode. */
  get(id: string): CommandHandle | null {
    const def = this.commands.get(id);
    if (!def) return null;
    return { def, active: this.isActive(def) };
  }

  /** All registered command IDs, sorted — a stable introspection surface. */
  ids(): string[] {
    return [...this.commands.keys()].sort();
  }

  /**
   * The full introspection model for the help UI / agent: every command with
   * its label, group, current-mode activeness, and the bindings that point at
   * it (resolved by the caller, since bindings live in the Keymap, not here).
   */
  list(): Array<{
    id: string;
    label: string;
    group?: string;
    active: boolean;
    modes: string[] | null;
  }> {
    return this.ids().map((id) => {
      const def = this.commands.get(id)!;
      return {
        id,
        label: def.label,
        group: def.group,
        active: this.isActive(def),
        modes: def.modes ? [...def.modes].sort() : null,
      };
    });
  }

  /** Activate a page/app mode. Global commands stay active; mode-scoped
   *  commands become active only when their mode matches. */
  setMode(mode: string | null): void {
    this.mode = mode;
  }

  get currentMode(): string | null {
    return this.mode;
  }

  private isActive(def: CommandDef): boolean {
    if (!def.modes) return true; // global
    return this.mode !== null && def.modes.has(this.mode);
  }

  /**
   * Dispatch a command by ID. Returns true when a registered AND active
   * command ran. A registered-but-inactive command (wrong mode) returns
   * false without running — the binding that resolved to it was not a match.
   * An unknown ID returns false. This is the ONE command function every
   * caller converges on.
   */
  run(id: string, caller?: CallerInfo, payload?: unknown): boolean {
    const def = this.commands.get(id);
    if (!def || !this.isActive(def)) return false;
    def.action(payload);
    return true;
  }
}

/** The registry the runtime wires up by default. */
export const globalRegistry = new CommandRegistry();
