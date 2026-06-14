"""CLI subcommand: ``scitex-ui lint <path>``.

Walks ``<path>`` (file or directory tree) and prints UI-101..105
violations in the standard ``path:line:col [RULE-ID] message`` format
that `scitex-linter` and `flake8` use. Exit code 0 if no violations, 1
otherwise — letting CI gate on the lint cleanly.

Wired up by ``scitex_ui._cli:main`` as a ``click`` subcommand and
re-exported via the ``scitex-ui`` console script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from ._checker import scan_path


@click.command(name="lint")
@click.argument(
    "target",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path),
)
@click.option(
    "--treat-as-consumer/--treat-as-scitex-ui",
    "treat_as_consumer",
    default=True,
    show_default=True,
    help=(
        "Treat the target as a CONSUMER repo (default — UI-104 fires "
        "on shell/primitive edits) or as SCITEX-UI ITSELF (UI-104 "
        "suppressed — shell/primitive edits are allowed from inside "
        "scitex-ui)."
    ),
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Emit one JSON object per violation (one per line, JSONL).",
)
def lint(target: Path, treat_as_consumer: bool, as_json: bool) -> None:
    """Scan TARGET for scitex-ui component-usage violations (UI-101..105).

    TARGET may be a directory or a single file. The walker recognises
    `.css`, `.html`, `.htm`, `.tsx`, `.jsx`, `.ts`, and `.js`; it
    skips `node_modules/`, `.venv/`, `.git/` etc. by default.

    Exit code is 0 when no violations are found, 1 otherwise.
    """
    violations = scan_path(target, treat_as_consumer=treat_as_consumer)
    if not violations:
        if not as_json:
            click.echo(f"OK: {target} — no UI-1xx violations found.")
        sys.exit(0)
    if as_json:
        import json

        for v in violations:
            click.echo(
                json.dumps(
                    {
                        "rule": v.rule.id,
                        "severity": v.rule.severity,
                        "path": v.path,
                        "line": v.line,
                        "col": v.col,
                        "message": v.rule.message,
                        "suggestion": v.rule.suggestion,
                        "source_line": v.source_line,
                    },
                    ensure_ascii=False,
                )
            )
    else:
        for v in violations:
            click.echo(f"{v.path}:{v.line}:{v.col} [{v.rule.id}] {v.rule.message}")
        click.echo(
            f"\n{len(violations)} violation(s) found. "
            "See _skills/scitex-ui/40_component-usage-doctrine.md for fixes."
        )
    sys.exit(1)


__all__ = ["lint"]
