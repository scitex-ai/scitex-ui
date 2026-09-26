# SciTeX design-system consultation — audit table + owner split

**Checkpoint 1 of the operator's design consultation (2026-09-17).** Reference artifact
reviewed as EVIDENCE: `/scratch/scitex-design-reference/scitex_science_platform.html`
(108,848 bytes, read-only). It is **not** copied and **not** shipped.

**Method:** every claim below is measured from the artifact or from scitex-ui's tree, not
inferred from either. Contrast ratios use the repo's own `tests/develop/_css_palette.contrast`
against the three shipped light surfaces (`--bg-page #faf9f7`, `--bg-surface #f8f7f5`,
`--bg-muted #f3f2f0`); worst surface is quoted.

---

## 0. Two facts that shape everything

1. **The mandated brand gradient `#2563eb → #1d4ed8` is essentially ABSENT from scitex-ui.**
   Measured: 2 incidental occurrences of `#2563eb` (`--status-info` fallback in
   `app/recent-pane.css`, `--_cta-hover` in `primitives/colors/_dark.css`) and **zero**
   `#1d4ed8`. It is a landing-page asset today, not a design-system token.
   *Both stops PASS AA as text on every light surface* (`#2563eb` 4.91/4.83/4.62;
   `#1d4ed8` 6.37/6.26/5.99) — so it can legally carry text, not only backgrounds.
2. **The reference's palette is a PARALLEL vocabulary, not a superset.** 19 tokens
   (`--ink --navy --navy-2 --navy-3 --paper --white --soft --muted --muted-light --line
   --line-dark --blue --blue-hover --mint --mint-dark --text-on-dark --radius --max
   --sans --mono`) against scitex-ui's **774 declarations** in families `--app-*` (186),
   `--stx-*` (121), `--workspace-*` (92), `--color-*` (78), `--status-*` (40),
   `--terminal-*` (40), `--role-*` (32), `--text-*` (27), `--bg-*` (21), `--border-*` (15).
   **Adopting the reference's names wholesale would be the worst available migration.**
   The good news: its *light* neutrals already agree in intent with scitex-ui's warm palette
   (`--paper #f5f4f0` vs `--bg-page #faf9f7`; `--soft #ebece8` vs `--bg-muted #f3f2f0`).

---

## A. Reusable — adopt (tokens / components / layout patterns)

| # | Reference source | scitex-ui target | Verdict | Drift |
|---|---|---|---|---|
| A1 | `--muted #64707a` | `--text-muted` (today `#777777`, **4.00 FAIL AA**) | **ADOPT as the muted value** — measured **4.53 PASS** on its worst light surface | 0 renames; one shared-token value. Needs the operator's define-vs-repoint ruling already outstanding |
| A2 | brand gradient `#2563eb→#1d4ed8` | **new** brand pair (`--stx-brand-from/-to`, plus a gradient utility) | **ADD** (mandated; absent today) — *preserve, do not change* | additive only |
| A3 | `--max:1264px` | no container token today | **ADD** one layout token (`--stx-container-max`) | additive |
| A4 | `--navy/-2/-3` dark surface steps | `--workspace-bg-primary/secondary/tertiary` + `_dark` `--_scitex-01..04` | **MAP** onto existing; no new names | 0 |
| A5 | `--muted-light #b2bdcb` | decorative only | **RESTRICT** to non-text (measured **1.70**, fails AA) — must never carry copy | rule, not token |
| A6 | `--blue #376bc5` / `--blue-hover #285aa9` | `--color-cta` (#3b82f6) + brand pair | **CONVERGE on the mandated pair** for brand surfaces; keep `--status-*` semantic | one decision, not a palette |
| A7 | `--mint/--mint-dark` | `--status-success` family | **MAP** | 0 |
| A8 | `--radius:7px` | existing radius vocabulary (effects tokens) | **MAP**; if it does not fit, one token, reasoned | 0–1 |
| A9 | `--sans/--mono` | `--font-mono` is consumed-but-undefined (carded); `--mono-font-family` exists | **MAP to defined names** — do not import a second font vocabulary | 0 |
| A10 | Section rhythm, task-first IA ("What does the data reveal?" → "Run it in your environment" → "Choose how you work with AI"), stat/step/card blocks, `class="i"` 17–24px stroke icon system | scitex-ui primitives (card/panel/sidebar-layout/empty/status-bar) + shell layout | **ADOPT the PATTERNS** (layout/composition), not the CSS | pattern-level |
| A11 | 390px discipline (fluid type, stacked sections) | `--stx-narrow-breakpoint` 768 / phone rules at 600 in `app-header`/`project-selector`/`selector-nav` | **RECONCILE to one boundary story** — the reference's mobile behaviour must not introduce a third breakpoint | rule |

## B. Operator approval required (copy / claims / provenance)

| # | Item | Why it needs the operator |
|---|---|---|
| B1 | Pricing / trial text | Artifact deliberately hard-codes none: *"Prices and trial promises are intentionally not hard-coded; links lead to the published pricing page."* Keep it that way; any on-landing price needs approval |
| B2 | Capability claims ("Run it in your environment", "Choose how you work with AI", integration lists) | Artifact: *"Integration and workflow availability must be confirmed in the production product."* Each claim needs an owner confirmation before it ships |
| B3 | SciTeX symbol/logo provenance | Artifact: *"The SciTeX symbol is taken from the product screenshot supplied by the project owner"* — confirm the artefact and licence for production |
| B4 | Reference-page influence (SciTeX · Claude Science) | Artifact uses them for audience context only and reuses no photography/artwork/testimonials — any *resemblance* claim or borrowed positioning needs approval |
| B5 | EN/JA parity of every adopted string | scitex-ui has the i18n layer (`gettext`, catalogs, `assert_no_untranslated`); landing copy must ship through it, not as literals |

## C. PROHIBITED in production (the artifact's own disclosure condemns these)

Quoted from the artifact itself:
- *"This is an illustrative product-design walkthrough, not a running SciTeX session. No files are uploaded and no tools, agents, or analyses are executed."*
- *"The workspace, charts, file relationships, and walkthroughs are illustrative. **Chart data are synthetic.**"*
- *"The preview does not establish the availability of a production feature or make scientific claims."*
- *"Stock photography is illustrative. **The people shown are not presented as SciTeX customers, employees, or endorsers.**"* (two Pexels photos: Edward Jenner; Tima Miroshnichenko)
- *"This design does not reuse the latter's photography, artwork, or testimonials."*

**Therefore, never in production:** synthetic chart data; illustrative workspace/"walkthrough"
UI; inline-SVG fake app screens; the two stock photos (or any stock person); any testimonial
not collected and approved; any capability claim the product cannot demonstrate.

## D. Replacements — real development-browser evidence only

| C-item | Replacement |
|---|---|
| Synthetic charts | Real screenshots/frames captured from a development browser running the actual app |
| Illustrative workspace + walkthroughs | Real dev screenshots (desktop **and** 390px) of the shipped shells — scitex-ui already produces these: this session's app-header and selector-nav canaries are exactly this class of evidence |
| Stock photography of people | No photography, or real product imagery. If people are ever shown, they are real users with a release |
| Feature claims in copy | Screenshot or short screen-recording of the feature working in dev, referenced by the claim |

---

## Lowest-drift migration path (the answer to "how", not just "what")

1. **Add, never rename.** Brand pair (A2) + container token (A3) + the AA-passing muted value
   (A1) are additive; `#2563eb→#1d4ed8` is preserved exactly as mandated.
2. **Map, never import** the reference's 19 names (A4/A6/A7/A8/A9). No second palette enters
   the tree; the token diff in the PR shows reference→existing for each.
3. **Patterns over CSS** (A10): section rhythm, IA and block vocabulary are composition
   decisions, so they belong in an RFC + examples, not in a new stylesheet.
4. **One breakpoint story** (A11): the reference must not add a third mobile boundary.
5. **Evidence before polish:** every visual claim in the eventual landing comes from a dev
   browser at desktop + 390px, captured by the same canary method already in use.

## Proposed owner split

| Owner | Scope |
|---|---|
| **scitex-ui (me)** | Token layer (A1–A3, additive), the reference→existing mapping table (A4–A9), component/layout patterns as RFC + examples (A10), breakpoint reconciliation (A11), the DESIGN/RFC artifact + token/component diff + desktop/390px evidence, in a dedicated branch/PR. **No leaf app changes, no merge** |
| **Hub landing owner** | The landing surface itself: hero/section composition, page copy, pricing/trial links, photography policy, analytics/JS policy, deployment. Coordinates which claims may appear and in what form |
| **Operator (approval gates)** | B1–B5 (pricing, capability claims, logo provenance, positioning, EN/JA parity), the A1 shared-token value change (131 consumed sites — same ruling as the AA card), and any palette change beyond additive brand tokens |
| **Leaf apps** | **Untouched** by this consultation, per the direction |

## Next checkpoint (proposed)

Branch `design/scitex-landing-rfc` with: the token diff as an actual patch (additive),
`docs/DESIGN_RFC_landing_and_apps.md`, and desktop + 390px screenshots captured from a
development browser. Then hold for the operator's ruling on A1/B1–B5 before anything is
applied to a shipped stylesheet.
