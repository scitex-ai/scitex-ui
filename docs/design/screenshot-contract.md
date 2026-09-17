# The screenshot contract — reusable capture component + caption

**Status:** proposed (operator-authorised 2026-09-17: real development screenshots/video
frames may be used for landing/design, replacing every illustrative surface).

**One rule above all others:** *an image may ship only with a manifest entry that proves
where it came from, and the caption must be RENDERED FROM that entry — never hand-typed.*
A caption typed next to an image is a claim about an image nobody re-checks; a caption
derived from the manifest cannot drift from it.

---

## Why this exists, from today's evidence

Capturing the app header, the selector-nav cascade, the mounted version badge, the PDF
fit-width fix and the empty-state measures produced **real frames at real viewports**, and
**every one was destroyed**: the browser harness writes a single default path
(`.../browser-harness/tmp/shot.png`), so the next capture overwrote the previous frame.
One file survives; five measurements are gone. That is not a tooling complaint, it is the
failure the contract prevents: **an un-catalogued capture is not evidence**, because nobody
— including its author, one hour later — can say which commit, which theme, which viewport
it showed.

---

## 1. The manifest (single source of truth)

One JSON file per capture set (e.g. `docs/design/captures/<surface>.json`):

```json
{
  "schema": "scitex-screenshot/1",
  "id": "app-header-390-light-en",
  "file": "app-header-390-light-en.png",
  "surface": { "app": "scitex-ui", "route": "/examples/app-header-canary" },
  "source_commit": "60dbb34",
  "environment": "dev-container",
  "captured_at": "2026-09-17T03:15:00Z",
  "viewport": { "width": 390, "height": 844, "dpr": 2, "mobile": true },
  "theme": "light",
  "locale": "en",
  "redaction": { "applied": true, "method": "fixture data only", "reason": "no personal data on screen" },
  "rights": { "owner": "scitex-ai", "license": "internal-product" },
  "supports": ["leaf version badge renders from the shell-props payload"],
  "verified_by": "tests/scitex_ui/vitest/app-header.test.ts + canary readback 2026-09-17T03:15Z"
}
```

### Required fields, and what each one forecloses

| Field | Type / enum | What it makes impossible |
|---|---|---|
| `source_commit` | 7–40 hex chars, **must exist in the repo** | a screenshot of some other branch, or of nothing |
| `environment` | closed enum: `dev-checkout` \| `dev-container` \| `staging` \| `production-approved` | an unreproducible or mislabelled capture ("it was production, probably") |
| `captured_at` | ISO-8601 UTC | undated evidence, which cannot be re-verified after the UI changes |
| `viewport` | width, height, dpr, mobile | a desktop shot presented as the mobile experience (and vice versa) |
| `theme` | `light` \| `dark` | half the product being invisible in the marketing claim |
| `locale` | `en` \| `ja` | a Japanese product shown only in English |
| `redaction` | explicit `applied` + `method` + `reason` | "it looked clean" standing in for a redaction decision |
| `rights` | owner + licence | stock imagery or third-party UI slipping in |
| `supports` | the claim(s) the image is evidence for | a pretty picture attached to a claim it does not show |
| `verified_by` | test path or readback id | an unverified result presented as a demonstrated capability |

### The four-variant rule

Each surface declares which of `{light, dark} × {en, ja}` it can show. A surface MAY ship
fewer than four, but the manifest must say so, and the landing must not imply more coverage
than exists. A missing variant is a fact, not a gap to be filled with a mockup.

## 2. The component (API sketch — implement after the operator's ruling)

```
<stx-shot id="app-header-390-light-en">
  → resolves the manifest entry, renders <figure> + the real file,
    and generates the caption from the SAME entry
</stx-shot>
```

Mirrors the repo's existing component shape (BEM `stx-shot`, CSS-first, `ts/app/shot/`,
server tag renders the manifest-backed figure so a page needs no JS). Behaviour:

1. **Refuses at build/render time** when the manifest entry is missing, when `file` is not on
   disk, when `source_commit` is not in the repo, when `environment` is outside the enum, or
   when `redaction.applied` is false without a written reason. Fail-closed, same as the
   version contract: a missing entry must never degrade to an uncaptioned image.
2. **Renders the caption from the entry** — surface, environment, `source_commit`, date,
   viewport, theme, locale — so caption/image cannot disagree.
3. **Emits a visible provenance line** on hover/focus and in the caption: `dev-container ·
   60dbb34 · 2026-09-17 · 390×844 @2x · light · en`.
4. **Never crops silently**: an image whose `supports` claim needs a region uses an explicit
   `crop` field, so the omitted area is a declared decision.

## 3. Prohibited, in the contract's own terms

- synthetic chart data, mockup UI, hand-drawn "app" SVG, AI-generated interface imagery;
- any capture with unredacted personal, credential, private-project or unpublished data;
- a caption that names a capability the image does not show (`verified_by` empty);
- a capture whose `source_commit` predates the feature it claims to show;
- reusing reference-page photography, artwork or testimonials (the design artifact's own
  constraint, kept verbatim).

## 4. Video frames

A still taken from a recording is a capture like any other and carries the same manifest, with
`captured_at` = the frame's timestamp and `file` pointing at the extracted frame (not the
video), plus `video` naming the source recording and its commit. A frame whose recording is
unavailable is not shippable evidence.
