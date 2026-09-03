/**
 * Type definitions for the Dim component — the presentation half of an
 * authorization verdict.
 *
 * THE VERDICT IS PRODUCED ELSEWHERE. `scitex_app.authz` builds it; this package
 * only renders it. The value crosses the package boundary as PLAIN SERIALISABLE
 * DATA (scitex-app's `Verdict.to_dict()`), which is why scitex-ui does not and
 * must not depend on scitex-app: an app depends on both of us, so importing the
 * SDK here would point that arrow backwards and every consumer would inherit it
 * through the presentation layer.
 *
 * THE FOUR KIND STRINGS BELOW ARE A SECOND COPY of scitex_app.authz's, in
 * another repo, and nothing in this file can detect a rename on their side.
 * scitex-app is building the check that can (it reads these constants out of
 * this package's shipped source), and it runs on THEIR side deliberately: the
 * breakage would appear here, but the cause is there, so a check nearest the
 * rename prevents rather than detects. Their caveat, recorded because it is
 * load-bearing: that leg is currently a RECORD, not a required context.
 */

/** Permitted. The only kind that is not a denial. */
export const ALLOWED = "allowed";

/** Refused, with no further recourse to offer. */
export const DENIED = "denied";

/** Refused because nobody is signed in. Carries a route. */
export const DENIED_NOT_SIGNED_IN = "denied-because-not-signed-in";

/** Refused because the signed-in account lacks the entitlement. */
export const DENIED_NOT_ENTITLED = "denied-because-not-entitled";

export type VerdictKind =
  | typeof ALLOWED
  | typeof DENIED
  | typeof DENIED_NOT_SIGNED_IN
  | typeof DENIED_NOT_ENTITLED;

export interface AllowedVerdict {
  kind: typeof ALLOWED;
}

export interface DeniedVerdict {
  kind: typeof DENIED;
}

export interface DeniedNotSignedInVerdict {
  kind: typeof DENIED_NOT_SIGNED_IN;
  /**
   * Where the user can go to sign in.
   *
   * REQUIRED, not optional, and that is enforced upstream rather than here:
   * scitex-app's validator REFUSES to build this kind without it, and refuses
   * to attach it to any other kind. So a verdict that reaches this component
   * cannot carry a sign-in route it has no business carrying, and cannot omit
   * one it promised. No defensive branch is written for either case on purpose
   * — an unnecessary guard is where a future bug hides, and it makes the
   * upstream guarantee look untrusted so the next reader adds another.
   */
  sign_in_url: string;
}

export interface DeniedNotEntitledVerdict {
  kind: typeof DENIED_NOT_ENTITLED;
  /** The entitlement the account is missing, e.g. a plan name. */
  entitlement: string;
  /**
   * NO ROUTE TODAY, and its absence is a decision rather than an oversight.
   *
   * "Sign in" is an action a user can take right now; "you are not on the paid
   * plan" may not be. Whether hub has an upgrade surface to send them to is
   * hub's fact, and scitex-app is asking rather than inventing it. Until there
   * is an answer, this kind renders inert — because a control that promises a
   * destination which does not exist is exactly the defect scitex-app's
   * validator refuses at the type level, relocated into CSS.
   *
   * WHEN IT ARRIVES it is an `upgrade_url` PAYLOAD on this interface, NOT a
   * fifth kind (scitex-app confirmed the shape 2026-09-03). That distinction is
   * why this switch is safe: adding a payload field is backward compatible and
   * leaves exhaustiveness intact, whereas a fifth kind would break it and needs
   * coordination on both sides.
   */
}

/**
 * A discriminated union, so a `switch` over `kind` is checked for
 * exhaustiveness by the compiler rather than by a reviewer.
 *
 * DELIBERATELY NO `allowed` BOOLEAN, here or anywhere in this component. A
 * helper like `isAllowed(v)` would be shorter than `v.kind === ALLOWED`, read
 * naturally, pass review, and silently collapse "sign in and this works" into
 * "this will never work" — the two-valued collapse of a genuinely multi-valued
 * answer. scitex-app asserts its absence on their side; a test in this repo
 * asserts it on ours, so the convenience cannot reappear without someone
 * deciding to add it.
 */
export type Verdict =
  | AllowedVerdict
  | DeniedVerdict
  | DeniedNotSignedInVerdict
  | DeniedNotEntitledVerdict;

/**
 * Human-readable reason text, one per denial.
 *
 * Configurable rather than hardcoded because this package already treats the
 * document language as dynamic (`shell_lang`), and a component that bakes
 * English strings into the accessible description would quietly undo that for
 * the one piece of text a screen-reader user most needs.
 */
export interface DimLabels {
  denied: string;
  deniedNotSignedIn: string;
  /** Receives the entitlement name via `{entitlement}`. */
  deniedNotEntitled: string;
}

export interface DimConfig {
  /** Override any subset of the reason strings. */
  labels?: Partial<DimLabels>;
}
