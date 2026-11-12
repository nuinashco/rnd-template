"""Migration to 1.0.0, which copier runs in a project made from an older release.

Usage:

    python to_1_0_0.py before .copier-answers.yml v0.3.4
    python to_1_0_0.py after .copier-answers.yml v0.3.4

`before` stops in a uni or lab project and names the copies that go; `after` clears what
copier left of them. The last argument is the release the project is on.
"""

from __future__ import annotations

import subprocess
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
KEPT = "kept in {folder}, since git has no copy of them: {names}"
# What releases before 1.0.0 copied into a project.
COPIES = (
    "src/nuikit",
    "tests/nuikit",
    "CONVENTIONS.md",
    ".claude/agents/conventions-reviewer.md",
    ".claude/agents/descriptions-judge.md",
)
# Release 0.1.0 named its nuikit `core`; in a later project that folder is its own code.
FIRST_COPIES = ("src/{package}/core", "tests/{package}/core")


def before(answers_file: str, release: str) -> None:
    """Stop in a uni or lab project; in an rnd one, name the copies that go."""
    answers = yaml.safe_load(Path(answers_file).read_text(encoding="utf-8"))
    profile = answers.get("profile", "rnd")
    if profile != "rnd":
        sys.exit(REFUSAL.format(profile=profile))
    present = [
        str(path)
        for path in copies(answers, release)
        if path.exists() or path.is_symlink()
    ]
    if present:
        print(NOTICE.format(copies=", ".join(present)))


def after(answers_file: str, release: str) -> None:
    """Remove what copier left of the copies; a file git has no copy of stays.

    A copy that is a symlink goes as a link: nothing in its target is touched.
    """
    answers = yaml.safe_load(Path(answers_file).read_text(encoding="utf-8"))
    for path in copies(answers, release):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            clear(path)


def copies(answers: dict[str, object], release: str) -> list[Path]:
    """Return where `release` put its copies in a project with these answers.

    A copy below a symlinked folder is left out: the migration never follows a symlink.
    """
    named = list(COPIES)
    if release.removeprefix("v").startswith("0.1."):
        named += [path.format(package=answers.get("package")) for path in FIRST_COPIES]
    paths = [Path(path) for path in named]
    return [path for path in paths if not any(map(Path.is_symlink, path.parents))]


def clear(folder: Path) -> None:
    """Delete the folder, except the files in it that only this machine has.

    A kept folder stays whole, and a symlink goes as a link.
    """
    kept = ignored(folder)
    for item in sorted(folder.rglob("*"), reverse=True):
        if any(path == item or path in item.parents for path in kept):
            continue
        if item.is_dir() and not item.is_symlink():
            if not any(item.iterdir()):
                item.rmdir()
        else:
            item.unlink()
    if kept:
        print(KEPT.format(folder=folder, names=", ".join(sorted(map(str, kept)))))
    else:
        folder.rmdir()


def ignored(folder: Path) -> set[Path]:
    """Return the files in `folder` that git has no copy of, bytecode caches aside.

    Nothing could bring them back. The tree is clean before an update, so they are the
    files the old .gitignore ignored, whatever the new one says. Git names a nested
    repository by its folder, not file by file.
    """
    command = ("git", "ls-files", "--others", "-z")
    listed = subprocess.run(
        [*command, "--", str(folder)], capture_output=True, text=True, check=True
    ).stdout
    names = (Path(name) for name in listed.split("\0") if name)
    return {name for name in names if "__pycache__" not in name.parts}


if __name__ == "__main__":
    stage, answers_file, release = sys.argv[1:4]
    if stage == "before":
        before(answers_file, release)
    else:
        after(answers_file, release)
