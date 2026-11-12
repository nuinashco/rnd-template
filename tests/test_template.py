"""Every variant of the template renders into a project whose own checks pass."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from copier import run_copy, run_update
from copier.errors import TaskError

VARIANTS = {
    "defaults": {},
    "py312-wandb": {"python": "3.12", "use_wandb": True},
    "no-example": {"example": False},
}
CHECKOUTS = {"nuikit_source": "NUIKIT_PATH", "hooks_source": "CONVENTIONS_PATH"}
SETTINGS = {
    "attribution": {"commit": "", "sessionUrl": False},
    "extraKnownMarketplaces": {
        "nuinashco": {
            "source": {"source": "github", "repo": "nuinashco/conventions"},
            "autoUpdate": True,
        }
    },
    "enabledPlugins": {"conventions@nuinashco": True, "nuikit@nuinashco": True},
}
OLD_RELEASE = "v0.3.4"  # The last release before 1.0.0, which still copied nuikit in.
# What projects made before 1.0.0 carried as copies, and its 1.0.0 migration removes.
VENDORED = [
    "src/nuikit/__init__.py",
    "tests/nuikit/test_config.py",
    "CONVENTIONS.md",
    ".claude/agents/conventions-reviewer.md",
    ".claude/agents/descriptions-judge.md",
]
TEMPLATE_RULES = {
    *("LAY-4", "LAY-7", "ENV-1", "ENV-2", "ENV-3", "TST-5", "TOOL-3"),
    *(f"RUN-{n}" for n in range(3, 8)),
}
EXAMPLE = [
    "src/demo/signals",
    "src/demo/stats",
    "tests/demo/signals",
    "tests/demo/stats",
    "configs/signal",
]
HEADING = re.compile(r"^### ([A-Z]+-\d+) (?:MUST|SHOULD|MAY)(?: \[rnd\])?$", re.M)


@pytest.fixture(scope="module")
def template(
    pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    # A plain copy: copier renders a git template from its last commit, and this
    # suite must test the working tree.
    src = tmp_path_factory.mktemp("template")
    shutil.copy(pytestconfig.rootpath / "copier.yml", src)
    shutil.copytree(pytestconfig.rootpath / "template", src / "template")
    return src


@pytest.fixture(scope="module", autouse=True)
def git_identity() -> Iterator[None]:
    """Name a committer for the repos the tests make: a CI machine has none."""
    with pytest.MonkeyPatch.context() as patch:
        for var in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
            patch.setenv(var, "template test")
        for var in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
            patch.setenv(var, "test@example.com")
        yield


@pytest.fixture(scope="module")
def sources() -> dict[str, str]:
    """Return the answers that install nuikit and conventions-hooks from checkouts.

    NUIKIT_PATH and CONVENTIONS_PATH name them. Without a variable there is no
    answer, and the project installs the release the template pins, as a user's does.
    """
    paths = {answer: os.environ.get(var) for answer, var in CHECKOUTS.items()}
    return {answer: local_source(Path(path)) for answer, path in paths.items() if path}


def local_source(checkout: Path) -> str:
    """Return the uv source that installs `checkout` as it is on disk.

    Editable, because uv rebuilds a plain path source only when its pyproject.toml
    changes, and would keep installing code from before the last edit.
    """
    path = json.dumps(str(checkout.expanduser().resolve()))
    return f"{{ path = {path}, editable = true }}"


@pytest.fixture(scope="module", params=VARIANTS, ids=list(VARIANTS))
def variant(request: pytest.FixtureRequest) -> dict[str, object]:
    return VARIANTS[request.param]


@pytest.fixture(scope="module")
def project(
    template: Path,
    sources: dict[str, str],
    variant: dict[str, object],
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Render the variant and install it."""
    dst = render(
        template, tmp_path_factory.mktemp("project") / "demo", **sources, **variant
    )
    sh(dst, "uv", "sync")
    return dst


@pytest.fixture(scope="module")
def rendered(
    template: Path, variant: dict[str, object], tmp_path_factory: pytest.TempPathFactory
) -> Path:
    """Render the variant with its default sources, without installing it."""
    return render(template, tmp_path_factory.mktemp("rendered") / "demo", **variant)


def render(
    template: Path, dst: Path, *, vcs_ref: str | None = None, **data: object
) -> Path:
    data = {"project_name": "demo", **data}
    run_copy(str(template), dst, data=data, vcs_ref=vcs_ref, defaults=True, quiet=True)
    sh(dst, "git", "init", "-q")
    return dst


def sh(cwd: Path, *args: str) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"{' '.join(args)}\n{result.stdout}\n{result.stderr}"
    return result.stdout


def python_files(project: Path) -> list[str]:
    return [str(p) for p in project.rglob("*.py") if ".venv" not in p.parts]


def test_project_passes_make_check(project):
    sh(project, "make", "check")


def test_run_command_writes_run_directory_with_outputs(project, variant):
    sh(project, "uv", "run", "demo-run", "run_name=smoke")

    written = {p.name for p in (project / "runs" / "smoke").iterdir()}
    outputs = {"summary.json"} if variant.get("example", True) else set()
    assert written == {"config.yaml", "run.json", *outputs}


def test_generated_configs_match_their_schemas(project):
    sh(project, "uv", "run", "demo-configs", "--check")


def test_python_files_follow_comment_rules(project):
    sh(project, "uv", "run", "check-comments", *python_files(project))


def test_python_files_follow_code_rules_an_ast_decides(project):
    sh(project, "uv", "run", "check-conventions", *python_files(project))


def test_check_protected_refuses_generated_files_only(project, variant):
    generated = ["configs/defaults/run.yaml", ".copier-answers.yml"]
    if variant.get("example", True):
        generated.append("configs/signal/gaussian.yaml")  # Marked by its header.
    editable = ["configs/run.yaml", "src/demo/paths.py", ".claude/rules/layout.md"]

    result = subprocess.run(
        ["uv", "run", "check-protected", *generated, *editable],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )

    listed = [line.split(":")[0] for line in result.stdout.splitlines()]
    assert listed == generated, result.stdout + result.stderr


def test_claude_settings_enable_plugins_and_leave_hooks_to_them(rendered):
    settings = json.loads((rendered / ".claude" / "settings.json").read_text())

    assert settings == SETTINGS


def test_project_carries_no_copy_of_nuikit_guide_or_subagents(rendered):
    copies = [
        path for path in [*VENDORED, ".claude/agents"] if (rendered / path).exists()
    ]

    assert copies == []


def test_example_domain_renders_only_when_asked(rendered, variant):
    present = [path for path in EXAMPLE if (rendered / path).is_dir()]

    assert present == (EXAMPLE if variant.get("example", True) else [])


def test_template_rules_are_path_scoped_and_shaped_as_rules(rendered):
    found = set()
    for path in sorted((rendered / ".claude" / "rules").glob("*.md")):
        _, frontmatter, body = path.read_text(encoding="utf-8").split("---\n", 2)
        rules = HEADING.split(body)[1:]
        found |= set(rules[::2])

        assert yaml.safe_load(frontmatter)["paths"], path.name
        assert all(
            text.strip().split("\n\n")[-1].startswith("*Check:* ")
            for text in rules[1::2]
        )
    assert found == TEMPLATE_RULES


def test_agents_file_stays_within_sixty_lines(rendered):
    lines = (rendered / "AGENTS.md").read_text(encoding="utf-8").splitlines()

    assert len(lines) <= 60


def test_make_lint_uses_conventions_release_that_projects_get(pytestconfig):
    root = pytestconfig.rootpath
    questions = yaml.safe_load((root / "copier.yml").read_text(encoding="utf-8"))
    pinned = re.findall(r'tag = "(.+)"', questions["hooks_source"]["default"])

    used = re.findall(r"conventions@(\S+)\)", (root / "Makefile").read_text("utf-8"))

    assert used == pinned


@pytest.fixture
def releases(template: Path, tmp_path: Path) -> Path:
    """Return a git copy of the template whose only release, v1.0.0, is this tree."""
    repo = tmp_path / "rnd-template"
    shutil.copytree(template, repo)
    sh(repo, "git", "init", "-q")
    commit(repo, "chore: release v1.0.0")
    sh(repo, "git", "tag", "v1.0.0")
    return repo


@pytest.fixture
def history(pytestconfig: pytest.Config, template: Path, tmp_path: Path) -> Path:
    """Return a clone of this repo whose newest release, v999.0.0, is this tree.

    The clone brings the real release tags, so a project can start from v0.3.4, the
    last release before 1.0.0, and update across it.
    """
    repo = tmp_path / "rnd-template"
    sh(pytestconfig.rootpath, "git", "clone", "-q", ".", str(repo))
    assert OLD_RELEASE in sh(repo, "git", "tag").split(), "run `git fetch --tags`"
    shutil.rmtree(repo / "template")
    shutil.copytree(template / "template", repo / "template")
    shutil.copy(template / "copier.yml", repo)
    commit(repo, "chore: release working tree")
    sh(repo, "git", "tag", "v999.0.0")
    return repo


def commit(repo: Path, message: str) -> None:
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "--allow-empty", "-m", message)


def update(project: Path, **data: object) -> None:
    """Update the project to the newest release, as `copier update --trust` would."""
    run_update(
        project, data=data, defaults=True, overwrite=True, unsafe=True, quiet=True
    )


def made_from_old_release(history: Path, dst: Path, *, profile: str = "rnd") -> Path:
    """Render a project from the last release before 1.0.0 and commit it."""
    render(history, dst, vcs_ref=OLD_RELEASE, profile=profile)
    commit(dst, "chore: start project")
    return dst


def test_update_from_old_release_removes_vendored_copies_and_says_so(
    history, tmp_path, capfd
):
    project = made_from_old_release(history, tmp_path / "old")
    carried = [path for path in VENDORED if (project / path).exists()]

    update(project)

    left = [path for path in VENDORED if (project / path).exists()]
    assert (carried, left) == (VENDORED, [])
    assert "1.0.0 removes src/nuikit" in capfd.readouterr().out


def test_update_from_old_release_leaves_example_out(history, tmp_path):
    project = made_from_old_release(history, tmp_path / "old")

    update(project)

    answers = yaml.safe_load((project / ".copier-answers.yml").read_text("utf-8"))
    present = [path for path in EXAMPLE if (project / path).exists()]
    assert (answers["example"], present) == (False, [])


def test_project_updated_from_old_release_passes_make_check(history, sources, tmp_path):
    project = made_from_old_release(history, tmp_path / "old")

    update(project, **sources)

    sh(project, "uv", "sync")
    sh(project, "make", "check")


@pytest.mark.parametrize("profile", ["uni", "lab"])
def test_update_of_uni_or_lab_project_is_refused_and_changes_nothing(
    history, tmp_path, capfd, profile
):
    project = made_from_old_release(history, tmp_path / "old", profile=profile)

    with pytest.raises(TaskError):
        update(project)

    assert sh(project, "git", "status", "--porcelain") == ""
    assert f"has no {profile} profile" in capfd.readouterr().err


def test_update_without_example_removes_example_domain(releases, tmp_path):
    project = tmp_path / "made"
    render(releases, project)
    commit(project, "chore: start project")

    update(project, example=False)

    config = (project / "src" / "demo" / "config.py").read_text(encoding="utf-8")
    assert ([p for p in EXAMPLE if (project / p).exists()], "signal" in config) == (
        [],
        False,
    )
