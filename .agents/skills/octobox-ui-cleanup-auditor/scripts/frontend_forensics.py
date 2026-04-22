#!/usr/bin/env python3
"""
Frontend forensics scanner for OctoBOX.

Use it to collect evidence before CSS/HTML cleanup, not to auto-delete code.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

IGNORED_PARTS = {
    ".git",
    ".venv",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "staticfiles",
    "tmp",
}
IGNORED_FRAGMENTS = (
    "docs\\backups\\",
    ".agents\\skills\\octobox-ui-cleanup-auditor\\",
)
MIRROR_TREE_ROOTS = {"octobox"}
USAGE_EXTENSIONS = {".html", ".js", ".py"}
CSS_EXTENSIONS = {".css"}
TEMPLATE_EXTENSIONS = {".html"}
RESIDUAL_SUFFIXES = (".bkp", ".bak", ".old")
LEGACY_FAMILIES = {
    "glass-panel": {"protected": False, "dead_when_unused": False},
    "finance-glass-panel": {"protected": False, "dead_when_unused": False},
    "elite-glass-card": {"protected": False, "dead_when_unused": True},
    "glass-panel-elite": {"protected": False, "dead_when_unused": True},
    "ui-card": {"protected": False, "dead_when_unused": True},
    "note-panel": {"protected": True, "dead_when_unused": False},
    "legacy-copy": {"protected": True, "dead_when_unused": False},
}


def normalized_path(path: Path) -> str:
    return str(path).replace("/", "\\").lower()


def relative_path(base: Path, path: Path) -> str:
    return path.resolve().relative_to(base).as_posix()


def relative_parts(base: Path, path: Path) -> tuple[str, ...]:
    try:
        rel = path.resolve().relative_to(base)
    except ValueError:
        return tuple(part.lower() for part in path.parts)
    return tuple(part.lower() for part in rel.parts)


def should_ignore(path: Path, base: Path, include_mirror_tree: bool = False) -> bool:
    rel_parts = relative_parts(base, path)
    if any(part in IGNORED_PARTS for part in rel_parts):
        return True
    if not include_mirror_tree and rel_parts and rel_parts[0] in MIRROR_TREE_ROOTS:
        return True
    lowered = normalized_path(path)
    return any(fragment in lowered for fragment in IGNORED_FRAGMENTS)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def line_at(text: str, number: int) -> str:
    lines = text.splitlines()
    if 1 <= number <= len(lines):
        return lines[number - 1].strip()
    return ""


def iter_files(
    base: Path,
    allowed_suffixes: set[str] | None = None,
    *,
    include_mirror_tree: bool = False,
) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if should_ignore(path, base, include_mirror_tree=include_mirror_tree):
            continue
        if allowed_suffixes and path.suffix.lower() not in allowed_suffixes:
            continue
        files.append(path)
    return files


def find_style_inline(template_files: list[Path], base: Path) -> list[dict]:
    findings = []
    pattern = re.compile(r'style\s*=\s*"([^"]+)"', re.IGNORECASE)
    for path in template_files:
        text = read_text(path)
        for match in pattern.finditer(text):
            ln = line_number(text, match.start())
            style_value = match.group(1).strip()
            findings.append(
                {
                    "classification": "override-hotspot",
                    "file": relative_path(base, path),
                    "line": ln,
                    "style": style_value,
                    "evidence": line_at(text, ln),
                    "reason": "inline style bypasses canonical CSS ownership",
                }
            )
    return findings


def find_style_blocks(template_files: list[Path], base: Path) -> list[dict]:
    findings = []
    pattern = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
    for path in template_files:
        text = read_text(path)
        for match in pattern.finditer(text):
            ln = line_number(text, match.start())
            snippet = match.group(1).strip().splitlines()
            preview = snippet[0].strip() if snippet else ""
            findings.append(
                {
                    "classification": "override-hotspot",
                    "file": relative_path(base, path),
                    "line": ln,
                    "evidence": preview,
                    "reason": "template-local style block can create hidden visual authority",
                }
            )
    return findings


def find_important_rules(css_files: list[Path], base: Path) -> list[dict]:
    findings = []
    for path in css_files:
        text = read_text(path)
        for match in re.finditer(r"!important", text, re.IGNORECASE):
            ln = line_number(text, match.start())
            findings.append(
                {
                    "classification": "override-hotspot",
                    "file": relative_path(base, path),
                    "line": ln,
                    "evidence": line_at(text, ln),
                    "reason": "uses !important",
                }
            )
    return findings


def find_residual_files(base: Path, *, include_mirror_tree: bool = False) -> list[dict]:
    findings = []
    for path in iter_files(base, include_mirror_tree=include_mirror_tree):
        lowered_name = path.name.lower()
        if path.suffix.lower() in RESIDUAL_SUFFIXES or any(
            token in lowered_name for token in (".bkp.", ".bak.", ".old.")
        ):
            findings.append(
                {
                    "classification": "dead",
                    "file": relative_path(base, path),
                    "reason": "residual backup or old artifact",
                }
            )
    return sorted(findings, key=lambda item: item["file"])


def collect_usage_corpus(base: Path, *, include_mirror_tree: bool = False) -> str:
    chunks = []
    for path in iter_files(base, USAGE_EXTENSIONS, include_mirror_tree=include_mirror_tree):
        chunks.append(read_text(path))
    return "\n".join(chunks)


def extract_rule_blocks(css_text: str) -> list[tuple[str, str, int]]:
    blocks = []
    pattern = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", re.DOTALL)
    for match in pattern.finditer(css_text):
        selector_group = " ".join(match.group("selectors").split())
        if not selector_group or selector_group.startswith("@"):
            continue
        blocks.append((selector_group, match.group("body"), line_number(css_text, match.start())))
    return blocks


def extract_class_names(selector: str) -> list[str]:
    return re.findall(r"\.([A-Za-z_][A-Za-z0-9_-]*)", selector)


def find_duplicate_selectors(css_files: list[Path], base: Path) -> list[dict]:
    selector_map: dict[str, list[dict]] = defaultdict(list)
    for path in css_files:
        text = read_text(path)
        for selector_group, _, ln in extract_rule_blocks(text):
            for selector in [item.strip() for item in selector_group.split(",") if item.strip()]:
                selector_map[selector].append(
                    {
                        "file": relative_path(base, path),
                        "line": ln,
                    }
                )

    findings = []
    for selector, occurrences in selector_map.items():
        distinct_files = {item["file"] for item in occurrences}
        if len(distinct_files) < 2:
            continue
        findings.append(
            {
                "classification": "duplicate-rule",
                "selector": selector,
                "occurrences": occurrences,
                "reason": "same selector defined in multiple files",
            }
        )
    return sorted(findings, key=lambda item: item["selector"])


def selector_depth(selector: str) -> int:
    parts = [part for part in re.split(r"\s+|>|\+|~", selector) if part]
    return len(parts)


def find_override_hotspots(css_files: list[Path], base: Path) -> list[dict]:
    findings = []
    for path in css_files:
        text = read_text(path)
        for selector_group, body, ln in extract_rule_blocks(text):
            for selector in [item.strip() for item in selector_group.split(",") if item.strip()]:
                reasons = []
                id_count = len(re.findall(r"#[A-Za-z0-9_-]+", selector))
                class_count = len(re.findall(r"\.[A-Za-z0-9_-]+", selector))
                attr_count = len(re.findall(r"\[[^\]]+\]", selector))
                depth = selector_depth(selector)
                if id_count:
                    reasons.append("contains id selector")
                if class_count + attr_count >= 4:
                    reasons.append("high selector density")
                if depth >= 5:
                    reasons.append("deep descendant chain")
                if len(selector) >= 90:
                    reasons.append("long selector")
                if "!important" in body:
                    reasons.append("block contains !important")
                if reasons:
                    findings.append(
                        {
                            "classification": "override-hotspot",
                            "file": relative_path(base, path),
                            "line": ln,
                            "selector": selector,
                            "reasons": reasons,
                        }
                    )
    return sorted(findings, key=lambda item: (item["file"], item["line"], item["selector"]))


def find_legacy_family_usage(
    scan_files: list[Path], base: Path
) -> tuple[list[dict], list[dict]]:
    occurrences = []
    summary = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for path in scan_files:
        text = read_text(path)
        rel = relative_path(base, path)
        for family, meta in LEGACY_FAMILIES.items():
            pattern = re.compile(rf"(?<![A-Za-z0-9_-])({re.escape(family)}[A-Za-z0-9_-]*)")
            for match in pattern.finditer(text):
                token = match.group(1)
                ln = line_number(text, match.start())
                classification = "canonical-alias" if meta["protected"] else "legacy-bridge"
                occurrence = {
                    "classification": classification,
                    "family": family,
                    "token": token,
                    "file": rel,
                    "line": ln,
                    "evidence": line_at(text, ln),
                }
                grouped[family].append(occurrence)
                occurrences.append(occurrence)

    for family, meta in LEGACY_FAMILIES.items():
        family_hits = grouped.get(family, [])
        if family_hits:
            classification = "canonical-alias" if meta["protected"] else "legacy-bridge"
        elif meta["protected"]:
            classification = "structural-do-not-touch"
        elif meta["dead_when_unused"]:
            classification = "dead"
        else:
            classification = "candidate-unused"
        summary.append(
            {
                "family": family,
                "classification": classification,
                "protected": meta["protected"],
                "hits": len(family_hits),
                "sample_files": sorted({item["file"] for item in family_hits})[:5],
            }
        )
    return sorted(summary, key=lambda item: item["family"]), sorted(
        occurrences, key=lambda item: (item["family"], item["file"], item["line"])
    )


def is_protected_alias(class_name: str) -> bool:
    return class_name.startswith("note-panel") or class_name.startswith("legacy-copy")


def find_candidate_unused_selectors(
    css_files: list[Path], usage_corpus: str, base: Path
) -> list[dict]:
    selector_definitions: dict[str, list[dict]] = defaultdict(list)
    for path in css_files:
        text = read_text(path)
        rel = relative_path(base, path)
        for selector_group, _, ln in extract_rule_blocks(text):
            for selector in [item.strip() for item in selector_group.split(",") if item.strip()]:
                for class_name in extract_class_names(selector):
                    selector_definitions[class_name].append(
                        {
                            "file": rel,
                            "line": ln,
                            "selector": selector,
                        }
                    )

    findings = []
    for class_name, definitions in selector_definitions.items():
        if is_protected_alias(class_name):
            continue
        usage_pattern = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(class_name)}(?![A-Za-z0-9_-])")
        if usage_pattern.search(usage_corpus):
            continue
        findings.append(
            {
                "classification": "candidate-unused",
                "class_name": class_name,
                "definitions": definitions[:5],
                "reason": "class selector not found in templates, JS, or Python strings",
            }
        )
    return sorted(findings, key=lambda item: item["class_name"])


def build_report(base: Path, *, include_mirror_tree: bool = False) -> dict:
    css_files = iter_files(base, CSS_EXTENSIONS, include_mirror_tree=include_mirror_tree)
    template_files = [
        path
        for path in iter_files(base, TEMPLATE_EXTENSIONS, include_mirror_tree=include_mirror_tree)
        if "templates" in normalized_path(path)
    ]
    scan_files = iter_files(
        base,
        CSS_EXTENSIONS | TEMPLATE_EXTENSIONS | {".js", ".py"},
        include_mirror_tree=include_mirror_tree,
    )
    usage_corpus = collect_usage_corpus(base, include_mirror_tree=include_mirror_tree)

    inline_styles = find_style_inline(template_files, base)
    style_blocks = find_style_blocks(template_files, base)
    important_rules = find_important_rules(css_files, base)
    residual_files = find_residual_files(base, include_mirror_tree=include_mirror_tree)
    duplicate_selectors = find_duplicate_selectors(css_files, base)
    override_hotspots = find_override_hotspots(css_files, base)
    legacy_summary, legacy_occurrences = find_legacy_family_usage(scan_files, base)
    candidate_unused = find_candidate_unused_selectors(css_files, usage_corpus, base)

    report = {
        "metadata": {
            "tool": "octobox-ui-cleanup-auditor/frontend_forensics.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "base_path": str(base),
            "include_mirror_tree": include_mirror_tree,
            "mirror_tree_roots": sorted(MIRROR_TREE_ROOTS),
        },
        "summary": {
            "important_rules": len(important_rules),
            "inline_styles": len(inline_styles),
            "style_blocks": len(style_blocks),
            "residual_files": len(residual_files),
            "duplicate_selectors": len(duplicate_selectors),
            "override_hotspots": len(override_hotspots),
            "legacy_family_occurrences": len(legacy_occurrences),
            "candidate_unused_selectors": len(candidate_unused),
        },
        "legacy_family_status": legacy_summary,
        "findings": {
            "important_rules": important_rules,
            "inline_styles": inline_styles,
            "style_blocks": style_blocks,
            "residual_files": residual_files,
            "duplicate_selectors": duplicate_selectors,
            "override_hotspots": override_hotspots,
            "legacy_family_occurrences": legacy_occurrences,
            "candidate_unused_selectors": candidate_unused,
        },
    }
    return report


def print_summary(report: dict) -> None:
    summary = report["summary"]
    print("--- Frontend Forensics Summary ---")
    print("!important rules:", summary["important_rules"])
    print("Inline style attributes:", summary["inline_styles"])
    print("Template <style> blocks:", summary["style_blocks"])
    print("Residual backup files:", summary["residual_files"])
    print("Duplicate selectors:", summary["duplicate_selectors"])
    print("Override hotspots:", summary["override_hotspots"])
    print("Legacy family occurrences:", summary["legacy_family_occurrences"])
    print("Candidate unused selectors:", summary["candidate_unused_selectors"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OctoBOX frontend forensics.")
    parser.add_argument("--base-path", default=".", help="Project root to scan")
    parser.add_argument("--report", required=True, help="Output JSON report path")
    parser.add_argument(
        "--include-mirror-tree",
        action="store_true",
        help="Include mirror-tree folders such as OctoBox/ in the scan.",
    )
    args = parser.parse_args()

    base = Path(args.base_path).resolve()
    report_path = Path(args.report).resolve()
    report = build_report(base, include_mirror_tree=args.include_mirror_tree)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_summary(report)
    print("Report:", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
