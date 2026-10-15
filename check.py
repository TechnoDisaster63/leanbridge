"""Dependency-free local checks. No installs, hosted services or network configuration."""
import ast
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)")


def check_sources(root=ROOT):
    errors = []
    paths = [root / "check.py"]
    for folder in ("src", "tests"):
        paths.extend(sorted((root / folder).rglob("*.py")))
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors


def check_links(root=ROOT):
    """Check inline local Markdown file targets, not external URLs or anchor IDs."""
    errors = []
    paths = list(root.glob("*.md")) + list((root / "docs").rglob("*.md"))
    for path in sorted(paths):
        for raw in LINK.findall(path.read_text(encoding="utf-8")):
            url = urlsplit(raw)
            if url.scheme or url.netloc or not url.path:
                continue
            target = (path.parent / unquote(url.path)).resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():
                errors.append(f"{path.relative_to(root)}: missing/outside target {raw}")
    return errors


def main():
    errors = check_sources() + check_links()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Source syntax and local Markdown file links: OK", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, env=env, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
