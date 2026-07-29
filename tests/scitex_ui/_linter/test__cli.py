"""Tests for ``scitex-ui lint`` — the CLI surface and its coverage notice.

The notice exists because "no violations found" is indistinguishable from
"nothing was looked at" unless the output says what it could not see.
scitex-dev made that a requirement on the EMITTED VERDICT rather than the
docs (2026-07-29), and STX-UI106 is a live example of the gap: it counts
``<option>`` tags in source, so a ``<select>`` populated at runtime is
invisible to it.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from scitex_ui._linter._cli import lint
from scitex_ui._linter._rules import COVERAGE_GAPS

_CLEAN = "body { color: var(--stx-text); }\n"
# 20 options with no filter and no opt-out — fires STX-UI106.
_DIRTY = "<select>" + "".join(f"<option>{i}</option>" for i in range(20)) + "</select>"


def _run(tmp_path: Path, name: str, body: str, *extra: str):
    (tmp_path / name).write_text(body)
    return CliRunner().invoke(lint, [str(tmp_path), *extra])


def test_clean_run_still_exits_zero(tmp_path: Path) -> None:
    # Arrange / Act
    result = _run(tmp_path, "a.css", _CLEAN)
    # Assert
    assert result.exit_code == 0


def test_clean_run_states_what_was_not_inspected(tmp_path: Path) -> None:
    # Arrange — the whole point. A clean verdict is where false closure is
    # cheapest to acquire.
    # Act
    result = _run(tmp_path, "a.css", _CLEAN)
    # Assert
    assert "NOT EVERYTHING WAS INSPECTED" in result.output


def test_clean_run_names_the_runtime_markup_gap(tmp_path: Path) -> None:
    # Arrange — naming the gap generically is not enough; the reader has to
    # learn that a JS-populated <select> is unseen by STX-UI106.
    # Act
    result = _run(tmp_path, "a.css", _CLEAN)
    # Assert
    assert "runtime" in result.output
    assert "STX-UI106" in result.output


def test_violation_run_also_states_the_gap(tmp_path: Path) -> None:
    # Arrange — a partial scan that DID find something still covers only
    # what it can see; reporting findings does not imply completeness.
    # Act
    result = _run(tmp_path, "page.html", _DIRTY)
    # Assert
    assert result.exit_code == 1
    assert "NOT EVERYTHING WAS INSPECTED" in result.output


def test_every_declared_gap_reaches_the_output(tmp_path: Path) -> None:
    # Arrange — guards the notice against drifting out of sync with the
    # data: a gap added to COVERAGE_GAPS but not rendered is a gap the
    # reader never learns about.
    # Act
    result = _run(tmp_path, "a.css", _CLEAN)
    # Assert
    for area, _detail in COVERAGE_GAPS:
        assert area in result.output


def test_json_mode_emits_a_coverage_record(tmp_path: Path) -> None:
    # Arrange — a machine reading an EMPTY violation stream has nothing
    # else to tell it the scan was partial, so JSON needs this most.
    # Act
    result = _run(tmp_path, "a.css", _CLEAN, "--json")
    # Assert
    records = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    coverage = [r for r in records if r.get("kind") == "coverage"]
    assert len(coverage) == 1
    assert len(coverage[0]["not_inspected"]) == len(COVERAGE_GAPS)


def test_json_mode_keeps_violations_parseable_alongside_coverage(
    tmp_path: Path,
) -> None:
    # Arrange — the coverage record must not corrupt the JSONL contract.
    # Act
    result = _run(tmp_path, "page.html", _DIRTY, "--json")
    # Assert
    records = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert any(r.get("kind") == "coverage" for r in records)
    assert any(r.get("rule") == "STX-UI106" for r in records)
