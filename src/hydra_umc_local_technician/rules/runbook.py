# =============================================================================
# HYDRA-UMC-LOCAL-TECHNICIAN - src/hydra_umc_local_technician/rules/runbook.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Runbooks in Markdown and the deterministic engine that reads them.

A runbook is a `.md` file: a front matter between two `---` lines, then sections.

    ---
    id: disk-nearly-full
    risk: prepare
    scope: the data partition of the server
    title: Data partition nearly full
    title.es: Particion de datos casi llena
    when: storage.usage partitions.0.usedPercent >= 90
    when: service.status active == true
    ---
    ## Diagnosis
    The data partition is above 90 percent.
    ## Diagnosis.es
    La particion de datos supera el 90 por ciento.
    ## Steps
    - Review the largest recordings.
    - Ask a person to archive the oldest ones.
    ## Rollback
    Nothing was changed: there is nothing to undo.

`when:` lines (all of them must hold) read `<tool> <path> <operator> <value>`; the path walks the `output` of that tool's result with
dots (`partitions.0.usedPercent`), the operators are `== != > >= < <= contains exists missing`, the value is JSON or plain text.
A missing tool result, a failed one or a missing field makes a condition false: the engine never guesses.

The engine only DECIDES which runbooks match and BUILDS a proposal through `propose_maintenance` (so every citation is grounded in
a real tool result). It has no way to run a step: a proposal is something a person approves, and nothing here executes it.
Text is chosen by language (`title.es`, `## Diagnosis.es`) with the default as fallback; the result is the same for the same input.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..escalation.evidence import ObservedResult
from ..escalation.proposal import propose_maintenance
from ..policy.risk_levels import RiskLevel
from ..settings import LANGUAGES

OPERATORS = (">=", "<=", "==", "!=", ">", "<", "contains", "exists", "missing")
_SECTIONS = {"diagnosis": "diagnosis", "steps": "steps", "rollback": "rollback", "pre-checks": "pre_checks",
             "expected changes": "expected_changes", "limits": "limits"}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_RUNBOOK_BYTES = 64 * 1024


class RunbookError(ValueError):
    """A runbook file is malformed."""


@dataclass(frozen=True)
class Condition:
    tool: str
    path: str
    operator: str
    value: Any


@dataclass
class Runbook:
    runbook_id: str
    risk: RiskLevel
    scope: dict[str, str]
    title: dict[str, str]
    conditions: list[Condition]
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    source: str = ""

    def text(self, key: str, language: str) -> Any:
        by_language = self.sections.get(key, {})
        return by_language.get(language, by_language.get(""))


@dataclass(frozen=True)
class Match:
    runbook: Runbook
    cited_tools: tuple[str, ...]


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _parse_condition(line: str, where: str) -> Condition:
    parts = line.split(None, 3)
    if len(parts) < 3:
        raise RunbookError(f"{where}: a condition is '<tool> <path> <operator> [value]'")
    tool, path, operator = parts[0], parts[1], parts[2]
    if operator not in OPERATORS:
        raise RunbookError(f"{where}: unknown operator {operator!r} (use {', '.join(OPERATORS)})")
    has_value = len(parts) == 4
    if operator in ("exists", "missing"):
        if has_value:
            raise RunbookError(f"{where}: {operator!r} takes no value")
        return Condition(tool, path, operator, None)
    if not has_value:
        raise RunbookError(f"{where}: operator {operator!r} needs a value")
    value = _parse_value(parts[3].strip())
    if operator in (">", ">=", "<", "<=") and (isinstance(value, bool) or not isinstance(value, (int, float))):
        raise RunbookError(f"{where}: operator {operator!r} needs a number")
    return Condition(tool, path, operator, value)


def _localized(key: str) -> tuple[str, str]:
    base, _, language = key.partition(".")
    return base, language


def parse_runbook(text: str, source: str = "runbook") -> Runbook:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise RunbookError(f"{source}: it must start with a front matter between '---' lines")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise RunbookError(f"{source}: the front matter is not closed with '---'") from error
    meta: dict[str, str] = {}
    scope: dict[str, str] = {}
    title: dict[str, str] = {}
    conditions: list[Condition] = []
    for number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            raise RunbookError(f"{source}:{number}: expected 'key: value'")
        key, value = key.strip(), value.strip()
        base, language = _localized(key)
        if language and language not in LANGUAGES:
            raise RunbookError(f"{source}:{number}: unknown language {language!r}")
        if base == "when" and not language:
            conditions.append(_parse_condition(value, f"{source}:{number}"))
        elif base == "title":
            title[language] = value
        elif base == "scope":
            scope[language] = value
        elif base in ("id", "risk") and not language:
            if base in meta:
                raise RunbookError(f"{source}:{number}: {base!r} is given twice")
            meta[base] = value
        else:
            raise RunbookError(f"{source}:{number}: unknown front matter key {key!r}")
    runbook_id = meta.get("id", "")
    if not _ID_RE.match(runbook_id):
        raise RunbookError(f"{source}: 'id' must be lowercase letters, digits and dashes")
    if not conditions:
        raise RunbookError(f"{source}: a runbook needs at least one 'when' condition (otherwise it would always match)")
    if "" not in title or "" not in scope:
        raise RunbookError(f"{source}: 'title' and 'scope' are required (the default text, without a language suffix)")
    try:
        risk = RiskLevel.from_wire_name(meta.get("risk", ""))
    except (ValueError, KeyError) as error:
        raise RunbookError(f"{source}: 'risk' is missing or not a known risk level") from error
    sections: dict[str, dict[str, Any]] = {}
    current: tuple[str, str] | None = None
    buffer: list[str] = []

    def close() -> None:
        if current is None:
            return
        key, language = current
        body = [line for line in buffer]
        if key in ("steps", "pre_checks", "expected_changes", "limits"):
            value: Any = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line).strip() for line in body if line.strip()]
        else:
            value = "\n".join(line.strip() for line in body if line.strip())
        sections.setdefault(key, {})[language] = value

    for raw in lines[end + 1:]:
        heading = re.match(r"^##\s+(.+?)\s*$", raw)
        if heading:
            close()
            buffer = []
            name, _, language = heading.group(1).partition(".")
            section = _SECTIONS.get(name.strip().lower())
            if section is None or (language and language not in LANGUAGES):
                raise RunbookError(f"{source}: unknown section {heading.group(1)!r}")
            current = (section, language)
        elif current is not None:
            buffer.append(raw)
    close()
    for key in ("diagnosis", "steps", "rollback"):
        if "" not in sections.get(key, {}) or not sections[key][""]:
            raise RunbookError(f"{source}: the section '{key}' is required (default text)")
    return Runbook(runbook_id, risk, scope, title, conditions, sections, source)


def load_runbooks(directory: Path) -> list[Runbook]:
    """Every `*.md` runbook of a directory, sorted by file name; one bad file is an error naming it (no silent skip)."""
    runbooks: list[Runbook] = []
    seen: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        if path.stat().st_size > MAX_RUNBOOK_BYTES:
            raise RunbookError(f"{path.name}: larger than {MAX_RUNBOOK_BYTES} bytes")
        runbook = parse_runbook(path.read_text(encoding="utf-8"), path.name)
        if runbook.runbook_id in seen:
            raise RunbookError(f"{path.name}: id {runbook.runbook_id!r} is already used by {seen[runbook.runbook_id]}")
        seen[runbook.runbook_id] = path.name
        runbooks.append(runbook)
    return runbooks


_MISSING = object()


def _walk(output: Any, path: str) -> Any:
    current = output
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


def _holds(condition: Condition, results: dict[str, dict[str, Any]]) -> bool:
    result = results.get(condition.tool)
    if result is None or result.get("status") != "ok":
        return False
    found = _walk(result.get("output", {}), condition.path)
    if condition.operator == "exists":
        return found is not _MISSING
    if condition.operator == "missing":
        return found is _MISSING
    if found is _MISSING:
        return False
    operator, expected = condition.operator, condition.value
    if operator == "==":
        return bool(found == expected and isinstance(found, bool) == isinstance(expected, bool))
    if operator == "!=":
        return not (found == expected and isinstance(found, bool) == isinstance(expected, bool))
    if operator == "contains":
        if isinstance(found, str):
            return str(expected) in found
        return isinstance(found, list) and expected in found
    if isinstance(found, bool) or not isinstance(found, (int, float)):
        return False
    return bool({">": found > expected, ">=": found >= expected, "<": found < expected, "<=": found <= expected}[operator])


def evaluate(runbooks: list[Runbook], results: dict[str, dict[str, Any]]) -> list[Match]:
    """The runbooks whose conditions all hold, in id order: the same results always give the same list."""
    matches = []
    for runbook in sorted(runbooks, key=lambda item: item.runbook_id):
        if all(_holds(condition, results) for condition in runbook.conditions):
            tools = tuple(sorted({condition.tool for condition in runbook.conditions}))
            matches.append(Match(runbook, tools))
    return matches


def build_proposal(match: Match, results: dict[str, dict[str, Any]], language: str = "en") -> dict[str, Any]:
    """A MaintenanceProposal from a matched runbook, citing the evidence of the tools its conditions read."""
    runbook = match.runbook
    pool = [ObservedResult(tool, results[tool]) for tool in match.cited_tools]
    return propose_maintenance(
        diagnosis=runbook.text("diagnosis", language), cited_evidence=[results[tool]["evidence"] for tool in match.cited_tools],
        evidence_pool=pool, scope=runbook.scope.get(language, runbook.scope[""]), risk=runbook.risk,
        steps=runbook.text("steps", language), rollback=runbook.text("rollback", language),
        pre_checks=runbook.text("pre_checks", language) or None, expected_changes=runbook.text("expected_changes", language) or None,
        explicit_limits=runbook.text("limits", language) or None,
    )
