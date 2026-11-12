"""Migration to 1.0.0, which copier runs in a project made from an older release.

Usage:

    python to_1_0_0.py before .copier-answers.yml    # stop in uni and lab, name copies
    python to_1_0_0.py after                         # clear what is left of them
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

REFUSAL = (
    "error: rnd-template 1.0.0 has no {profile} profile, so this project stays on the "
    "release it was made from; nothing was changed"
)
NOTICE = (
    "1.0.0 removes {copies}, local edits included: nuikit and the plugins bring them "
    "now. Until you commit the update, `git show HEAD:<path>` prints one, so you can "
    "move a change into your own package."
)
# What releases before 1.0.0 copied into a project.
COPIES = (
    "src/nuikit",
    "tests/nuikit",
    "CONVENTIONS.md",
    ".claude/agents/conventions-reviewer.md",
    ".claude/agents/descriptions-judge.md",
)
# v0.1.0 named its nuikit `core`; copier removes those files itself.
FIRST_COPIES = ("src/{package}/core", "tests/{package}/core")


def before(answers_file: str) -> None:
    """Stop in a uni or lab project; in an rnd one, name the copies that go."""
    answers = yaml.safe_load(Path(answers_file).read_text(encoding="utf-8"))
    profile = answers.get("profile", "rnd")
    if profile != "rnd":
        sys.exit(REFUSAL.format(profile=profile))
    named = [*COPIES, *(p.format(package=answers.get("package")) for p in FIRST_COPIES)]
    copies = [path for path in named if Path(path).exists()]
    if copies:
        print(NOTICE.format(copies=", ".join(copies)))


def after() -> None:
    """Remove what copier left of the copies: files no release rendered."""
    for path in map(Path, COPIES):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


if __name__ == "__main__":
    if sys.argv[1] == "before":
        before(sys.argv[2])
    else:
        after()
