/**
 * Keymap primitive: chord parsing, registry dispatch, runtime behaviour
 * (mode shadowing, input suppression, prefix expiry, lifecycle), and the
 * help() introspection model. `npx vitest run`
 *
 * The harness drives Keymap.handleKeydown through attach(document) and
 * dispatches plain objects that carry the keyboard fields — no real
 * KeyboardEvent is constructed, so the suite is portable across jsdom
 * versions and workers.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommandRegistry,
  Keymap,
  parseChord,
  parseSequence,
  sequenceKey,
  chordToString,
  eventToChord,
} from "../../../src/scitex_ui/static/scitex_ui/ts/shell/keymap";

/* ── Chord grammar ─────────────────────────────────────────────────────── */

describe("chord parsing", () => {
  it("parses a bare letter key case-insensitively", () => {
    expect(parseChord("x").key).toBe("x");
    expect(parseChord("X").key).toBe("x");
  });

  it("parses the Emacs modifier tokens C/M/S/M2 into flags", () => {
    expect(parseChord("C-x")).toEqual({ ctrl: true, alt: false, shift: false, meta: false, key: "x" });
    expect(parseChord("M-g")).toEqual({ ctrl: false, alt: true, shift: false, meta: false, key: "g" });
    expect(parseChord("S-A")).toEqual({ ctrl: false, alt: false, shift: true, meta: false, key: "a" });
    expect(parseChord("M2-C-RET")).toEqual({ ctrl: true, alt: false, shift: false, meta: true, key: "return" });
  });

  it("maps named keys to their canonical single-token form", () => {
    expect(parseChord("RET").key).toBe("return");
    expect(parseChord("SPAC").key).toBe(" ");
    expect(parseChord("ESC").key).toBe("escape");
    expect(parseChord("F1").key).toBe("F1");
    expect(parseChord("UP").key).toBe("up");
  });

  it("parses a prefix-command sequence into multiple chords", () => {
    const seq = parseSequence("C-x C-s");
    expect(seq).toHaveLength(2);
    expect(seq[0]).toMatchObject({ ctrl: true, key: "x" });
    expect(seq[1]).toMatchObject({ ctrl: true, key: "s" });
  });

  it("round-trips a chord through sequenceKey deterministically", () => {
    expect(sequenceKey(parseSequence("C-x C-s"))).toBe("C-X C-S");
    expect(chordToString(parseChord("M-g"))).toBe("M-G");
  });

  it("eventToChord ignores bare modifier presses (no command intent)", () => {
    expect(eventToChord({ key: "Shift", ctrlKey: false, altKey: false, shiftKey: true, metaKey: false })).toBeNull();
    expect(eventToChord({ key: "Control", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false })).toBeNull();
  });

  it("eventToChord canonicalizes a real Ctrl+X keydown the same as parseChord('C-x')", () => {
    const fromEvent = eventToChord({ key: "x", ctrlKey: true, altKey: false, shiftKey: false, metaKey: false });
    expect(fromEvent).toEqual(parseChord("C-x"));
  });
});

/* ── Registry: one command function, stable IDs, mode activeness ───────── */

describe("CommandRegistry", () => {
  it("runs a registered command through the single dispatch path", () => {
    const reg = new CommandRegistry();
    const calls: Array<unknown> = [];
    reg.set({ id: "save", label: "Save", action: (p) => calls.push(p) });
    expect(reg.run("save", { via: "keyboard" }, "payload")).toBe(true);
    expect(calls).toEqual(["payload"]);
  });

  it("returns false for an unknown command id", () => {
    const reg = new CommandRegistry();
    expect(reg.run("missing")).toBe(false);
  });

  it("keeps a mode-scoped command inactive until its mode is active", () => {
    const reg = new CommandRegistry();
    const ran: string[] = [];
    reg.set({ id: "editor:undo", label: "Undo", modes: new Set(["editor"]), action: () => ran.push("undo") });
    reg.run("editor:undo");
    expect(ran).toEqual([]);
    reg.setMode("editor");
    reg.run("editor:undo");
    expect(ran).toEqual(["undo"]);
  });

  it("lists commands with stable sorted ids and their active flag", () => {
    const reg = new CommandRegistry();
    reg.set({ id: "b", label: "B", action: () => {} });
    reg.set({ id: "a", label: "A", action: () => {} });
    reg.set({ id: "c", label: "C", modes: new Set(["m"]), action: () => {} });
    reg.setMode("m");
    expect(reg.ids()).toEqual(["a", "b", "c"]);
    const list = reg.list();
    expect(list.find((x) => x.id === "c")!.active).toBe(true);
    reg.setMode(null);
    expect(reg.list().find((x) => x.id === "c")!.active).toBe(false);
  });
});

/* ── Keymap runtime ────────────────────────────────────────────────────── */

function key(opts: { key: string; ctrl?: boolean; alt?: boolean; shift?: boolean; meta?: boolean; target?: EventTarget | null }): any {
  const prevented = { called: false };
  return {
    key: opts.key,
    ctrlKey: !!opts.ctrl,
    altKey: !!opts.alt,
    shiftKey: !!opts.shift,
    metaKey: !!opts.meta,
    target: opts.target ?? null,
    preventDefault: () => { prevented.called = true; },
    _prevented: prevented,
  };
}

describe("Keymap runtime", () => {
  let reg: CommandRegistry;
  let map: Keymap;
  let detachFn: (() => void) | undefined;

  beforeEach(() => {
    document.body.innerHTML = "";
    reg = new CommandRegistry();
    map = new Keymap({ registry: reg });
    detachFn = map.attach(document);
  });

  it("fires a global binding on a full chord and swallows the key", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    const ev = key({ key: "s", ctrl: true });
    map["handleKeydown"](ev as any);
    expect(reg.get("save")!.active).toBe(true);
    expect(ev._prevented.called).toBe(true);
  });

  it("detects a chord conflict when binding the same chord to a different command", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "close", label: "Close", action: vi.fn() });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    const conflict = map.bind("global", "C-s", "close");
    expect(conflict).not.toBeNull();
    expect(conflict!.existingCommandId).toBe("save");
    expect(conflict!.newCommandId).toBe("close");
    // the original binding is not clobbered silently
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("save");
  });

  it("resolves a mode binding in preference to a global one (shadowing)", () => {
    reg.set({ id: "global-s", label: "G", action: vi.fn() });
    reg.set({ id: "editor-s", label: "E", action: vi.fn() });
    expect(map.bind("global", "C-s", "global-s")).toBeNull();
    expect(map.bind("editor", "C-s", "editor-s")).toBeNull();
    map.activateMode("editor");
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("editor-s");
    map.deactivateMode();
    expect(map.resolve(parseSequence("C-s"))!.commandId).toBe("global-s");
  });

  it("tracks a multi-chord prefix and fires only when it completes", () => {
    const run = vi.fn();
    reg.set({ id: "save-buffer", label: "Save buffer", action: run });
    expect(map.bind("global", "C-x C-s", "save-buffer")).toBeNull();
    // first chord is a live prefix: swallowed, not fired
    map["handleKeydown"](key({ key: "x", ctrl: true }) as any);
    expect(run).not.toHaveBeenCalled();
    // completing chord fires
    map["handleKeydown"](key({ key: "s", ctrl: true }) as any);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("expires a dead-end prefix and lets the next key be fresh", () => {
    const run = vi.fn();
    reg.set({ id: "solo", label: "Solo", action: run });
    expect(map.bind("global", "C-s", "solo")).toBeNull();
    // 'c' is not the start of any bound sequence -> pending stays empty
    map["handleKeydown"](key({ key: "c" }) as any);
    // then a bare C-s still fires
    map["handleKeydown"](key({ key: "s", ctrl: true }) as any);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("suppresses chords inside an input unless the binding opted in", () => {
    const run = vi.fn();
    reg.set({ id: "copy", label: "Copy", action: run });
    expect(map.bind("global", "C-c", "copy")).toBeNull(); // NOT inInput
    const input = document.createElement("input");
    document.body.appendChild(input);
    map["handleKeydown"](key({ key: "c", ctrl: true, target: input }) as any);
    expect(run).not.toHaveBeenCalled(); // suppressed in the field

    reg.set({ id: "term", label: "Term", action: run });
    expect(map.bind("global", "C-c", "term", true)).not.toBeNull(); // conflict: C-c already bound
    // unbind the non-input one so the inInput one can occupy the chord
    map.unbind("copy");
    expect(map.bind("global", "C-c", "term", true)).toBeNull();
    map["handleKeydown"](key({ key: "c", ctrl: true, target: input }) as any);
    expect(run).toHaveBeenCalledTimes(1); // fires because inInput
  });

  it("converges button/agent/program dispatch on the same command", () => {
    const run = vi.fn();
    reg.set({ id: "run", label: "Run", action: run });
    expect(map.bind("global", "C-r", "run")).toBeNull();
    expect(map.dispatchSequence("C-r", "agent")).toBe("run");
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("attach() returns a detach that removes the keydown listener (lifecycle cleanup)", () => {
    const removeSpy = vi.spyOn(document, "removeEventListener");
    expect(document.removeEventListener).not.toHaveBeenCalled();
    // The detach returned by attach() must remove exactly the keydown listener.
    detachFn!();
    expect(removeSpy).toHaveBeenCalledWith("keydown", map["onKeydown"], true);
    removeSpy.mockRestore();
  });

  it("help() reports the active mode and the chords bound to each command", () => {
    reg.set({ id: "save", label: "Save", action: vi.fn() });
    reg.set({ id: "ed:undo", label: "Undo", action: vi.fn(), modes: new Set(["editor"]) });
    expect(map.bind("global", "C-s", "save")).toBeNull();
    expect(map.bind("editor", "M-/", "ed:undo")).toBeNull();
    map.activateMode("editor");
    const help = map.help();
    expect(help.mode).toBe("editor");
    const save = help.commands.find((c) => c.id === "save")!;
    expect(save.chords).toContain("C-S");
    const undo = help.commands.find((c) => c.id === "ed:undo")!;
    expect(undo.active).toBe(true);
    expect(undo.chords).toContain("M-/");
  });
});
