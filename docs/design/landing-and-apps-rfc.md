# DESIGN/RFC — a cohesive SciTeX experience across landing and apps

**Checkpoint 2 (2026-09-17).** Operator authorisation: real development screenshots/video
frames may be used for landing and design. This RFC replaces every illustrative surface from
the reference artifact with **a real browser-captured product surface** or **an abstract
non-product visual**, defines the screenshot component/caption contract, and proposes which
real surfaces best demonstrate the product.

Reference artifact (evidence only, never copied, never shipped):
`/scratch/scitex-design-reference/scitex_science_platform.html` — 108,848 bytes, read-only.

---

## 1. Illustrative → real, item by item (the audit's category D, rewritten)

The reference's own disclosure condemns its illustrative material (*"an illustrative
product-design walkthrough, not a running SciTeX session… Chart data are synthetic"*). Each
C-item now has a replacement that EXISTS or is capturable today:

| # | Illustrative item (prohibited) | Replacement surface | Real capture available? |
|---|---|---|---|
| D1 | Synthetic charts / "what does the data reveal" visual | **Stats** (real analysis output) or **FigRecipe** canvas with a real figure | Yes — a leaf's own dev server; FigRecipe/Stats owners hold the routes |
| D2 | Illustrative workspace ("the workspace… is illustrative") | **scitex-ui shell** as shipped: sidebar + module pane + AI panel at desktop, and the same shell at 390 (single-pane stack) | **Yes, today** — captures taken this session at 390×844 (shell + header + mounted version badge) |
| D3 | Walkthrough / step-through UI frames | **Sequence of real frames** of one task done in a dev browser (open project → pick file → run → read result), each frame a manifest entry | Yes, as a scripted capture session |
| D4 | Inline-SVG fake app screens | **Abstract non-product visuals** (geometry/gradient compositions in the brand pair) for any slot where no real surface exists yet | Yes — abstract is always available, and it claims nothing |
| D5 | Two Pexels photos of people | **No photography**, or scitex-ui's own icon/illustration vocabulary | Yes — removal is the default |
| D6 | Feature claims in copy | **The feature's own screenshot**, `supports` naming the claim, `verified_by` naming its test | Per feature, as each lands |

**Rule adopted from the reference and kept:** where no real surface exists yet, ship an
**abstract non-product visual** — never a mockup. An abstract visual is honest; a mockup is a
claim about a product that does not exist.

## 2. The screenshot contract (separate file, same branch)

`docs/design/screenshot-contract.md` defines `scitex-screenshot/1`: a manifest with
`source_commit`, `environment` (closed enum), `captured_at`, `viewport`, `theme`, `locale`,
`redaction`, `rights`, `supports`, `verified_by`; a `stx-shot` component that **renders the
caption from the manifest** and **refuses to render** when any required field is absent; and
the four-variant rule `{light,dark} × {en,ja}` with an explicit declaration of which variants
a surface has.

**Why it is written as fail-closed, from this session's own evidence:** the six real frames I
captured today (app header at 390, its long-title truncation, the selector-nav cascade before
and after, the mounted version badge, the PDF fit-width fix) were all written to the browser
harness's single default path and **overwritten by the next capture**. One file survives. An
un-catalogued capture is not evidence — nobody, including its author one hour later, can say
which commit and viewport it showed. The contract exists so that cannot recur.

## 3. Which real surfaces best demonstrate the product (proposal)

Ranked by (demonstrates the claim) × (capturable today) × (no leaf-app change needed):

1. **The shell itself, desktop + 390px, light + dark** — it is the product's spine and every
   claim about "a workspace that fits your lab" is a claim about this surface. Capturable from
   scitex-ui's own standalone shell: no leaf coordination required.
2. **Project context in the header** — title + version badge + project picker in one row,
   because "connected project context" is otherwise an assertion. The version badge is now
   backed by a real contract (`data-app-version`, this session) and its `verified_by` names it.
3. **The AI panel doing one real thing** (choose chat vs console, run one command) — "choose
   how you work with AI" is the claim most in need of a frame that shows a choice being made.
4. **A real result surface** — Stats or FigRecipe with an actual figure/analysis. Highest
   persuasive value, needs the leaf owner's participation (video/growth coordination).
5. **Mobile continuity** — the same three surfaces at 390px, since "works on mobile" is
   currently the claim with the least evidence.

Abstract visuals fill the rest; they are the honest default.

## 4. Migration path (unchanged from checkpoint 1, restated for this authorisation)

Additive only: brand pair (`#2563eb→#1d4ed8`, preserved exactly) + container token + the
AA-passing muted candidate (`#64707a`, measured 4.53 worst-surface PASS, versus
`--text-muted #777777` at 4.00 FAIL).
No reference token names enter the tree; every one maps onto an existing scitex-ui token.
Patterns (IA, section rhythm, block vocabulary) stay composition-level, in this RFC and
examples, not in a new stylesheet.

## 5. Owner split (unchanged; the screenshot work sharpens it)

| Owner | Scope |
|---|---|
| **scitex-ui (me)** | Token layer (additive), mapping table, patterns, breakpoints, **the screenshot contract + `stx-shot`**, and the shell/header/mobile captures (surfaces I own) |
| **Hub landing owner** | Landing composition, copy, pricing links, photography policy, JS/analytics policy |
| **Video / growth agents** | The demo sequence (D3), the result-surface frames (D1: Stats/FigRecipe), and which claims each frame is allowed to support. Handles to confirm — no design/video/growth card exists in the store today, and I will not invent one without the operator naming the owner |
| **Operator** | B1–B5, the AA muted value (131 sites), any palette change beyond additive brand tokens |
| **Leaf apps** | Untouched |

## 6. What this RFC does NOT do

No shipped stylesheet is modified. No leaf app is touched. Nothing is merged. The next step
after the operator's ruling is a single additive patch (brand pair + container + muted value)
plus real captures under the manifest, at which point the landing can be composed from
evidence rather than from a mockup.
