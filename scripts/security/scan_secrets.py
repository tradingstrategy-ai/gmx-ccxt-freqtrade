#!/usr/bin/env python3
"""Scan repository files for secrets before they enter git history.

Standalone secret scanner — no external dependencies beyond Python stdlib.
Uses the same detection patterns as web3-ethereum-defi's sensitive_filter
but does not import from it (avoids submodule path issues in git hooks).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Secret detection patterns (mirrored from sensitive_filter.py)
# ---------------------------------------------------------------------------

_EXACT_HEX_KEY_RE = re.compile(r"^\s*(?:0x)?[0-9a-fA-F]{64}\s*$")
_CONTEXTUAL_HEX_KEY_RE = re.compile(
    r"(?i)\b(?:private(?:[_\s-]?key)?|secret|seed|signing(?:[_\s-]?key)?)\b"
    r"[^\n\r]{0,32}?(?:0x)?[0-9a-fA-F]{64}\b"
)
_PEM_KEY_RE = re.compile(
    r"-----BEGIN (?:EC |RSA |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
)
_ED25519_SECRET_RE = re.compile(r"ed25519:[A-Za-z0-9+/=]{32,}")
_FIELD_PATTERNS = [
    re.compile(r"""['"]apiKey['"]:\s*['"]([^'"]{16,})['"]""", re.IGNORECASE),
    re.compile(r"""['"]secret['"]:\s*['"]([^'"]{16,})['"]""", re.IGNORECASE),
    re.compile(r"""['"]password['"]:\s*['"]([^'"]+)['"]""", re.IGNORECASE),
    re.compile(r"""['"]jwt_secret_key['"]:\s*['"]([^'"]+)['"]""", re.IGNORECASE),
    re.compile(
        r"""['"]privateKey['"]:\s*['"](?:0x)?([0-9a-fA-F]{64,})['"]""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""['"]private_key['"]:\s*['"](?:0x)?([0-9a-fA-F]{64,})['"]""",
        re.IGNORECASE,
    ),
    re.compile(
        r"""['"]signature['"]:\s*['"](0x[0-9a-fA-F]{64,})['"]""",
        re.IGNORECASE,
    ),
]


def contains_secret(text: str) -> bool:
    """Return True if *text* contains anything that looks like a secret."""
    if _EXACT_HEX_KEY_RE.search(text):
        return True
    if _CONTEXTUAL_HEX_KEY_RE.search(text):
        return True
    if _PEM_KEY_RE.search(text):
        return True
    if _ED25519_SECRET_RE.search(text):
        return True
    return any(pattern.search(text) for pattern in _FIELD_PATTERNS)


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

SCAN_EXTENSIONS = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".rst",
    ".txt",
    ".cfg",
    ".ini",
    ".env",
    ".sh",
    ".ipynb",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


def scan_text(text: str, filepath: str) -> list[str]:
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        if contains_secret(line):
            findings.append(f"  {filepath}:{i} — contains a potential secret")
    return findings


def _iter_text_fragments(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text_fragments(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_text_fragments(item)


def scan_notebook(content: str, filepath: str) -> list[str]:
    findings = []
    try:
        notebook = json.loads(content)
    except json.JSONDecodeError:
        return [f"  {filepath}: failed to parse as JSON"]

    for i, cell in enumerate(notebook.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        if contains_secret(source):
            findings.append(f"  {filepath}: cell {i} source contains a potential secret")

        for output in cell.get("outputs", []):
            if any(contains_secret(fragment) for fragment in _iter_text_fragments(output)):
                findings.append(f"  {filepath}: cell {i} output contains a potential secret")
                break

    return findings


def scan_content(content: str, suffix: str, filepath: str) -> list[str]:
    if suffix == ".ipynb":
        return scan_notebook(content, filepath)
    return scan_text(content, filepath)


def scan_file(filepath: Path) -> list[str]:
    try:
        content = filepath.read_text(errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_content(content, filepath.suffix, str(filepath))


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def scan_staged() -> list[str]:
    findings = []
    staged_files = _git_output("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines()

    for path_str in staged_files:
        filepath = REPO_ROOT / path_str
        if filepath.suffix not in SCAN_EXTENSIONS:
            continue

        staged = subprocess.run(
            ["git", "show", f":{path_str}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if staged.returncode == 0:
            findings.extend(scan_content(staged.stdout, filepath.suffix, path_str))
    return findings


def _range_target(rev_range: str) -> str:
    if "..." in rev_range:
        return rev_range.split("...", 1)[1]
    if ".." in rev_range:
        return rev_range.split("..", 1)[1]
    return rev_range


def scan_commit_range(rev_range: str) -> list[str]:
    findings = []
    changed_files = _git_output("diff", "--name-only", "--diff-filter=ACMR", rev_range).splitlines()
    target_rev = _range_target(rev_range)

    for path_str in changed_files:
        filepath = REPO_ROOT / path_str
        if filepath.suffix not in SCAN_EXTENSIONS:
            continue
        blob = subprocess.run(
            ["git", "show", f"{target_rev}:{path_str}"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if blob.returncode == 0:
            findings.extend(scan_content(blob.stdout, filepath.suffix, path_str))
    return findings


def scan_all() -> list[str]:
    findings = []
    for filepath in REPO_ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in filepath.parts):
            continue
        if filepath.is_file() and filepath.suffix in SCAN_EXTENSIONS:
            findings.extend(scan_file(filepath))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan repository files for secrets")
    parser.add_argument("--staged", action="store_true", help="Scan git staged files only")
    parser.add_argument("--range", type=str, help="Scan a git commit range")
    parser.add_argument("--all", action="store_true", help="Scan entire working tree")
    args = parser.parse_args()

    try:
        if args.staged:
            findings = scan_staged()
        elif args.range:
            findings = scan_commit_range(args.range)
        else:
            findings = scan_all()
    except RuntimeError as exc:
        print(f"Secret scan failed: {exc}", file=sys.stderr)
        sys.exit(2)

    if findings:
        print("SECRET SCAN FAILED — potential secrets detected:\n")
        for finding in findings:
            print(finding)
        print(f"\n{len(findings)} finding(s). Remove secrets before committing.")
        sys.exit(1)

    print("Secret scan: clean")


if __name__ == "__main__":
    main()
