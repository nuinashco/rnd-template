"""Before an update to 1.0.0: stop in a uni or lab project, say what an rnd one loses.

Usage:

    python before_1_0_0.py .copier-answers.yml    # copier runs it in the project
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REFUSAL = (
    "error: rnd-template 1.0.0 has no {profile} profile, so this project stays on the "
    "release it was made from; nothing was changed"
)
# What releases before 1.0.0 copied into a project; v0.1.0 named its nuikit `core`.
COPIES = (
    "src/nuikit",
    "tests/nuikit",
    "src/{package}/core",
    "tests/{package}/core",
    "CONVENTIONS.md",
    ".claude/agents/conventions-reviewer.md",
    ".claude/agents/descriptions-judge.md",
)
NOTICE = (
    "1.0.0 removes {copies}, local edits included: nuikit and the plugins bring them "
    "now. Until you commit the update, `git show HEAD:<path>` prints one, so you can "
    "move a change into your own package."
)


def main(answers_file: str) -> None:
    answers = yaml.safe_load(Path(answers_file).read_text(encoding="utf-8"))
    profile = answers.get("profile", "rnd")
    if profile != "rnd":
        sys.exit(REFUSAL.format(profile=profile))
    paths = [copy.format(package=answers.get("package")) for copy in COPIES]
    copies = [path for path in paths if Path(path).exists()]
    if copies:
        print(NOTICE.format(copies=", ".join(copies)))


if __name__ == "__main__":
    main(sys.argv[1])
