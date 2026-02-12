"""Generate a table of contents for README.md based on Markdown headings.

Inserts or updates the TOC above the "# Overview" section.

Usage:
    python scripts/generate_toc.py
"""

import re
import sys
from pathlib import Path

README_PATH = Path(__file__).resolve().parent.parent / "README.md"

TOC_START = "<!-- TOC START -->"
TOC_END = "<!-- TOC END -->"


def heading_to_anchor(text: str) -> str:
    """Convert heading text to a GitHub-compatible anchor link."""
    # Remove markdown links but keep link text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove inline code backticks
    text = text.replace("`", "")
    # Remove bold/italic markers
    text = text.replace("**", "").replace("*", "")
    # Lowercase, replace spaces with hyphens, strip non-alphanumeric (except hyphens)
    anchor = text.lower().strip()
    anchor = re.sub(r"[^\w\s-]", "", anchor)
    anchor = re.sub(r"\s+", "-", anchor)
    return anchor


def extract_headings(lines: list[str]) -> list[tuple[int, str]]:
    """Extract (level, text) for each Markdown heading, skipping the first h1 and fenced code blocks."""
    headings = []
    in_code_block = False
    skipped_first_h1 = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()

            if level == 1 and not skipped_first_h1:
                skipped_first_h1 = True
                continue

            headings.append((level, text))

    return headings


def build_toc(headings: list[tuple[int, str]]) -> str:
    """Build the TOC markdown string."""
    if not headings:
        return ""

    min_level = min(h[0] for h in headings)
    toc_lines = [TOC_START, "## Table of Contents", ""]

    for level, text in headings:
        indent = "  " * (level - min_level)
        anchor = heading_to_anchor(text)
        toc_lines.append(f"{indent}- [{text}](#{anchor})")

    toc_lines.append("")
    toc_lines.append(TOC_END)
    return "\n".join(toc_lines)


def main():
    if not README_PATH.exists():
        print(f"Error: {README_PATH} not found", file=sys.stderr)
        sys.exit(1)

    content = README_PATH.read_text()

    # Remove existing TOC before extracting headings
    existing_toc = re.search(
        rf"^{re.escape(TOC_START)}.*?^{re.escape(TOC_END)}\n?",
        content,
        re.MULTILINE | re.DOTALL,
    )
    if existing_toc:
        before = content[: existing_toc.start()].rstrip("\n")
        after = content[existing_toc.end() :].lstrip("\n")
        content = before + "\n\n" + after

    lines = content.splitlines()

    headings = extract_headings(lines)
    if not headings:
        print("No headings found in README.md", file=sys.stderr)
        sys.exit(1)

    toc_block = build_toc(headings)

    # Insert above "# Overview"
    overview_match = re.search(r"^# Overview", content, re.MULTILINE)
    if not overview_match:
        print("Error: '# Overview' heading not found in README.md", file=sys.stderr)
        sys.exit(1)

    insert_pos = overview_match.start()
    new_content = content[:insert_pos] + toc_block + "\n\n" + content[insert_pos:]

    README_PATH.write_text(new_content)
    print(f"Table of contents ({len(headings)} entries) written to {README_PATH}")


if __name__ == "__main__":
    main()
