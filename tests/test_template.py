"""Every variant of the template renders into a project whose own checks pass."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from copier import run_copy, run_update
from copier.errors import TaskError, UnsafeTemplateError
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

VARIANTS = {
    "defaults": {},
    "py312-wandb": {"python": "3.12", "use_wandb": True},
    "no-example": {"example": False},
}
CHECKOUTS = {"nuikit_source": "NUIKIT_PATH", "hooks_source": "CONVENTIONS_PATH"}
# In the key order Claude Code writes, so that installing a plugin changes nothing.
SETTINGS = {
    "attribution": {"commit": "", "sessionUrl": False},
    "enabledPlugins": {"conventions@nuinashco": True, "nuikit@nuinashco": True},
    "extraKnownMarketplaces": {
        "nuinashco": {
            "source": {"source": "github", "repo": "nuinashco/conventions"},
            "autoUpdate": True,
        }
    },
}
LONGEST_NAME = "longest-name-a-package-gets"  # 27 characters, the limit of `package`.
PACKAGE = re.compile(r"[a-z][a-z0-9_]*")
QUESTIONS = 8
# Prints, as JSON, which installed distributions each importable name comes from.
MODULES = (
    "import json; from importlib.metadata import packages_distributions as found; "
    "print(json.dumps(found()))"
)
STDLIB = "import json, sys; print(json.dumps(sorted(sys.stdlib_module_names)))"
# Answers that once broke the render: quotes and a backslash for TOML, letters outside
# ASCII and more than a line's worth of text for the package docstring.
AWKWARD = {
    "project_name": LONGEST_NAME,
    "description": (
        'Reproduces "Attention Is All You Need" from C:\\data, na\u00efvely \u2014 '
        "and says so at a length no line of Python would hold"
    ),
    "author_name": 'Zo\u00eb "Zed" O\'Neil',
}
# A script as LAY-7 allows it: matplotlib is declared here, and the project lacks it.
FIGURE_SCRIPT = """\
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "matplotlib>=3.9",
# ]
# ///
\"\"\"Plot the loss of one run for a note.\"\"\"

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

run_dir = Path(sys.argv[1])
lines = (run_dir / "metrics.jsonl").read_text(encoding="utf-8").splitlines()
plt.plot([json.loads(line)["loss"] for line in lines])
plt.savefig(run_dir / "loss.png")
"""
# A developer's signing key does not fit the identity these tests commit with.
UNSIGNED = ("-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false")
NOTEBOOK = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["import os, sys\n", "print( 'explored' )"],
        }
    ],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5,
}
SHIPPED = (
    "template",
    "migrations",
    "includes",
)  # What copier reads besides copier.yml.
OLD_RELEASE = "v0.3.4"  # The last release before 1.0.0, which still copied nuikit in.
FIRST_RELEASE = "v0.1.0"  # The only one whose copy of nuikit was `src/<package>/core/`.
# What a project made from an old release on GitHub carries; a clone renders a path.
OLD_HOOKS_SOURCE = (
    'conventions-hooks = { git = "https://github.com/nuinashco/conventions", '
    'rev = "de61fac6f3b8f22d2a0e468f1d264a507b0d6275" }'
)
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
REWRITING = ("end-of-file-fixer", "trailing-whitespace", "nbstripout")
HEADING = re.compile(r"^### ([A-Z]+-\d+) (?:MUST|SHOULD|MAY)(?: \[rnd\])?$", re.M)
BASH_BLOCK = re.compile(r"^ *```bash\n(.*?)^ *```$", re.M | re.S)
INSTALLS = ["/plugin install conventions@nuinashco", "/plugin install nuikit@nuinashco"]


@pytest.fixture(scope="module")
def template(
    pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory
) -> Path:
    # A plain copy: copier renders a git template from its last commit, and this
    # suite must test the working tree.
    src = tmp_path_factory.mktemp("template")
    shutil.copy(pytestconfig.rootpath / "copier.yml", src)
    for folder in SHIPPED:
        shutil.copytree(pytestconfig.rootpath / folder, src / folder)
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


def test_run_with_negative_seed_exits_with_config_error_that_names_seed(project):
    result = subprocess.run(
        ["uv", "run", "demo-run", "seed=-1"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "  seed: " in result.stderr


@pytest.fixture
def head(project: Path) -> Iterator[str]:
    """Give the project a first commit and return its SHA; take it back afterwards."""
    sh(project, "git", *UNSIGNED, "commit", "-q", "--allow-empty", "-m", "chore: start")
    yield sh(project, "git", "rev-parse", "HEAD").strip()
    sh(project, "git", "update-ref", "-d", "HEAD")


def test_run_started_outside_project_records_commit_of_project(project, head, tmp_path):
    sh(tmp_path, "uv", "run", "--project", str(project), "demo-run", "run_name=away")

    run = json.loads((project / "runs" / "away" / "run.json").read_text("utf-8"))
    assert run["git_sha"] == head


def test_sweep_named_as_readme_says_gives_each_job_its_run_directory(project):
    name = "run_name=sweep_${hydra:job.num}"
    assert name in (project / "README.md").read_text(encoding="utf-8")

    sweep = subprocess.run(
        ["uv", "run", "demo-run", "-m", "seed=1,2", name],
        cwd=project / "scripts",
        capture_output=True,
        text=True,
        check=True,
    )

    assert (project / "runs" / "sweep_0" / "run.json").is_file()
    assert (project / "runs" / "sweep_1" / "run.json").is_file()
    # Each job logs the run directory it wrote, the second as well as the first.
    assert [job for job in ("sweep_0", "sweep_1") if job not in sweep.stderr] == []
    # Hydra's sweep folder lands at the root, where git ignores it.
    assert (project / "multirun").is_dir()
    assert not (project / "scripts" / "multirun").exists()


@pytest.fixture
def script(project: Path) -> Iterator[Path]:
    """Name a one-off script in `scripts/` and remove it for the tests that follow."""
    path = project / "scripts" / "plot_loss.py"
    yield path
    path.unlink(missing_ok=True)


@pytest.mark.parametrize("target", ["lint", "typecheck"])
def test_script_that_declares_its_own_dependency_passes(script, target):
    script.write_text(FIGURE_SCRIPT, encoding="utf-8")

    sh(script.parents[1], "make", target)


def test_type_error_in_script_still_fails_typecheck(script):
    script.write_text('"""Count."""\n\ncount: int = "three"\n', encoding="utf-8")

    result = subprocess.run(
        ["make", "typecheck"],
        cwd=script.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "plot_loss.py" in result.stdout


@pytest.fixture
def module(project: Path) -> Iterator[Path]:
    """Name a new module of the package and remove it for the tests that follow."""
    path = project / "src" / "demo" / "scale.py"
    yield path
    path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("source", "finding"),
    [
        (
            '\ndef scale(values, factor):\n    """Scale."""\n    return values\n',
            "ANN001",
        ),
        ('UNIT = "caf\u00e9"\n', "STY-8"),
    ],
    ids=["signature-without-types", "letter-outside-ascii"],
)
def test_lint_names_what_module_breaks(module, source, finding):
    header = '"""Scaling."""\n\nfrom __future__ import annotations\n\n'
    module.write_text(header + source, encoding="utf-8")

    result = subprocess.run(
        ["make", "lint"],
        cwd=module.parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert finding in result.stdout


@pytest.fixture
def deleted(project: Path) -> Iterator[Path]:
    """Track a module, then delete it as an update does before the user commits."""
    path = project / "src" / "demo" / "retired.py"
    path.write_text('"""Retired."""\n', encoding="utf-8")
    sh(project, "git", "add", str(path))
    path.unlink()
    yield path
    sh(project, "git", "rm", "-q", "--cached", str(path))


def test_lint_says_nothing_of_tracked_module_deleted_from_working_tree(deleted):
    result = subprocess.run(
        ["make", "lint"],
        cwd=deleted.parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert deleted.name not in result.stdout + result.stderr


def test_integration_target_passes_while_no_test_carries_its_marker(project):
    sh(project, "make", "test-integration")


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

    assert (settings, list(settings)) == (SETTINGS, list(SETTINGS))


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


def test_gitignore_ignores_top_level_folders_and_keeps_packages_named_like_them(
    rendered,
):
    # `data` and `runs` alone are what git sees of a symlink to another disk.
    paths = ["data/raw.csv", "runs/first/run.json", "dist/demo.whl", "data", "runs"]
    packages = ["src/demo/data/loaders.py", "tests/demo/runs/test_latest.py"]

    ignored = sh(rendered, "git", "check-ignore", *paths, *packages).split()

    assert ignored == paths


def test_lock_file_stays_in_git_where_machine_ignores_lock_files(rendered, tmp_path):
    (tmp_path / "ignore").write_text("*.lock\n", encoding="utf-8")
    machine = f"core.excludesFile={tmp_path / 'ignore'}"

    result = subprocess.run(
        ["git", "-c", machine, "check-ignore", "-q", "uv.lock"],
        cwd=rendered,
        check=False,
    )

    assert result.returncode == 1  # Git's code for a path that no pattern ignores.


def test_hooks_that_rewrite_files_skip_reference_notebooks(rendered):
    text = (rendered / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    hooks = {
        hook["id"]: hook
        for repo in yaml.safe_load(text)["repos"]
        for hook in repo["hooks"]
    }

    skipped = {name: hooks[name].get("exclude") for name in REWRITING}
    assert skipped == dict.fromkeys(REWRITING, "^notebooks/reference/")


def commented_commands(*documents: Path) -> list[str]:
    """Return the lines of the documents' bash blocks that carry a comment."""
    return [
        f"{document.name}: {line.strip()}"
        for document in documents
        for block in BASH_BLOCK.findall(document.read_text(encoding="utf-8"))
        for line in block.splitlines()
        if "#" in line
    ]


def test_command_blocks_of_documents_hold_only_commands(pytestconfig, rendered):
    # An interactive zsh hands a trailing `# comment` to the command as arguments.
    documents = [
        folder / name
        for folder in (pytestconfig.rootpath, rendered)
        for name in ("README.md", "CONTRIBUTING.md")
    ]
    documents.append(pytestconfig.rootpath / "UPGRADING.md")

    assert commented_commands(*documents) == []


def test_both_readmes_give_install_command_of_each_plugin(pytestconfig, rendered):
    readmes = [pytestconfig.rootpath / "README.md", rendered / "README.md"]

    missing = [
        (readme.parent.name, command)
        for readme in readmes
        for command in INSTALLS
        if command not in readme.read_text(encoding="utf-8")
    ]

    assert missing == []


def test_agents_file_stays_within_sixty_lines(rendered):
    lines = (rendered / "AGENTS.md").read_text(encoding="utf-8").splitlines()

    assert len(lines) <= 60


def test_make_lint_uses_conventions_release_that_projects_get(pytestconfig):
    root = pytestconfig.rootpath
    questions = yaml.safe_load((root / "copier.yml").read_text(encoding="utf-8"))
    pinned = re.findall(r'tag = "(.+)"', questions["hooks_source"]["default"])

    used = re.findall(r"conventions@(\S+)\)", (root / "Makefile").read_text("utf-8"))

    assert used == pinned


def answers_of(project: Path) -> dict[str, object]:
    return yaml.safe_load((project / ".copier-answers.yml").read_text("utf-8"))


@pytest.mark.parametrize(
    ("folder", "name"), [("folder-name", "folder-name"), ("My_Project", "my-project")]
)
def test_project_is_named_after_its_folder_by_default(template, tmp_path, folder, name):
    run_copy(str(template), tmp_path / folder, defaults=True, quiet=True)

    assert answers_of(tmp_path / folder)["project_name"] == name


@pytest.mark.parametrize(
    ("folder", "typed", "names"),
    [
        ("2026-eval", ["eval-2026"], ("eval-2026", "eval_2026")),
        (LONGEST_NAME + "x", ["", "shorter"], (LONGEST_NAME + "x", "shorter")),
    ],
    ids=["folder-starts-with-digit", "package-too-long"],
)
def test_name_that_folder_cannot_give_is_asked_for_and_typed(
    template, tmp_path, folder, typed, names
):
    # Copier reads the answers from a pipe as it does from a keyboard: one line each,
    # an empty one for the default.
    lines = [*typed, *[""] * (QUESTIONS - len(typed))]

    subprocess.run(
        [sys.executable, "-m", "copier", "copy", str(template), str(tmp_path / folder)],
        input="".join(f"{line}\n" for line in lines),
        capture_output=True,
        text=True,
        check=True,
    )

    answers = answers_of(tmp_path / folder)
    assert (answers["project_name"], answers["package"]) == names


def test_awkward_answers_render_valid_toml_and_code_that_passes_ruff(
    template, tmp_path
):
    project = render(template, tmp_path / "awkward", **AWKWARD)

    sh(project, sys.executable, "-m", "ruff", "check")
    sh(project, sys.executable, "-m", "ruff", "format", "--check")
    metadata = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))["project"]
    written = (metadata["description"], metadata["authors"][0]["name"])
    assert written == (AWKWARD["description"], AWKWARD["author_name"])
    assert all(Path(path).read_bytes().isascii() for path in python_files(project))


def test_line_break_in_answer_becomes_space_in_project_metadata(template, tmp_path):
    project = render(template, tmp_path / "broken", description="Two\nlines")

    metadata = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))["project"]
    assert metadata["description"] == "Two lines"


def test_ruff_leaves_exploration_notebooks_alone(template, tmp_path):
    project = render(template, tmp_path / "explored")
    (project / "notebooks" / "explore.ipynb").write_text(json.dumps(NOTEBOOK), "utf-8")

    sh(project, sys.executable, "-m", "ruff", "check")
    sh(project, sys.executable, "-m", "ruff", "format", "--check")


@pytest.mark.parametrize(
    ("answers", "reason"),
    [
        ({"project_name": "demo-"}, "kebab-case"),
        ({"project_name": "hydra-core"}, "dependency's name"),
        ({"project_name": "p" * 51, "package": "demo"}, "50 characters"),
        ({"project_name": LONGEST_NAME + "x"}, "27 characters"),
        ({"package": "lambda"}, "keyword"),
        ({"project_name": "signal"}, "hides a module"),
        ({"package": "dotenv"}, "hides a module"),
        ({"package": "utils"}, "LAY-2"),
    ],
    ids=[
        "trailing-dash",
        "dependency",
        "project-too-long",
        "package-too-long",
        "keyword",
        "stdlib-module",
        "installed-module",
        "grab-bag",
    ],
)
def test_name_that_cannot_work_is_refused_with_its_reason(
    template, tmp_path, answers, reason
):
    with pytest.raises(ValueError, match=reason):
        render(template, tmp_path / "refused", **answers)


@pytest.fixture(scope="module")
def names(pytestconfig: pytest.Config) -> object:
    """Return the macros that refuse names, loaded the way copier loads them."""
    env = SandboxedEnvironment(
        loader=FileSystemLoader(pytestconfig.rootpath),
        extensions=["jinja2_ansible_filters.AnsibleCoreFiltersExtension"],
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("includes/names.jinja").module


@pytest.mark.parametrize("python", ["3.12", "3.13", "3.14"])
def test_no_module_of_standard_library_is_accepted_as_package(names, tmp_path, python):
    found = sh(
        tmp_path, "uv", "run", "--no-project", "-p", python, "python", "-c", STDLIB
    )
    modules = sorted(filter(PACKAGE.fullmatch, json.loads(found)))

    accepted = [name for name in modules if not str(names.package_refusal(name))]

    assert accepted == []


def test_no_dependency_named_in_pyproject_is_accepted_as_package_or_project(
    project, names
):
    metadata = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))
    asked = [
        *metadata["project"]["dependencies"],
        *metadata["dependency-groups"]["dev"],
    ]
    wanted = {distribution(re.split(r"[^\w.-]", line)[0]) for line in asked}
    found = json.loads(sh(project, "uv", "run", "python", "-c", MODULES))
    modules = {
        module
        for module, sources in found.items()
        if wanted & {distribution(source) for source in sources}
    }

    accepted = [
        *(name for name in sorted(wanted) if not str(names.project_refusal(name))),
        *(
            name
            for name in sorted(modules | {name.replace("-", "_") for name in wanted})
            if PACKAGE.fullmatch(name) and not str(names.package_refusal(name))
        ),
    ]

    assert accepted == []


def distribution(name: str) -> str:
    """Return the name in the form package indexes compare: lowercase, with dashes."""
    return re.sub(r"[-_.]+", "-", name).lower()


@pytest.fixture
def releases(template: Path, tmp_path: Path) -> Path:
    """Return a git copy of the template whose only release, v1.0.0, is this tree."""
    repo = tmp_path / "rnd-template"
    shutil.copytree(template, repo)
    sh(repo, "git", "init", "-q")
    commit(repo, "chore: release v1.0.0")
    sh(repo, "git", *UNSIGNED, "tag", "v1.0.0")
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
    for folder in SHIPPED:
        shutil.rmtree(repo / folder, ignore_errors=True)
        shutil.copytree(template / folder, repo / folder)
    shutil.copy(template / "copier.yml", repo)
    commit(repo, "chore: release working tree")
    sh(repo, "git", *UNSIGNED, "tag", "v999.0.0")
    return repo


def commit(repo: Path, message: str) -> None:
    sh(repo, "git", "add", "-A")
    sh(repo, "git", *UNSIGNED, "commit", "-q", "--allow-empty", "-m", message)


def update(project: Path, *, trust: bool = False, **data: object) -> None:
    """Update the project to the newest release, as `copier update --defaults` would.

    `trust` stands for `--trust`, which copier asks for when a migration runs.
    """
    run_update(
        project, data=data, defaults=True, overwrite=True, unsafe=trust, quiet=True
    )


def made_from_old_release(
    history: Path,
    dst: Path,
    *,
    release: str = OLD_RELEASE,
    profile: str = "rnd",
    files: dict[str, str] | None = None,
    **data: object,
) -> Path:
    """Render a project from a release before 1.0.0, add `files` and commit it."""
    render(history, dst, vcs_ref=release, profile=profile, **data)
    write(dst, files or {})
    commit(dst, "chore: start project")
    return dst


def write(project: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        (project / name).write_text(text, encoding="utf-8")


def test_update_from_old_release_removes_vendored_copies_and_says_so(
    history, tmp_path, capfd
):
    project = made_from_old_release(history, tmp_path / "old")
    carried = [path for path in VENDORED if (project / path).exists()]

    update(project, trust=True)

    left = [path for path in VENDORED if (project / path).exists()]
    assert (carried, left) == (VENDORED, [])
    assert "1.0.0 removes src/nuikit" in capfd.readouterr().out


def test_file_owner_added_to_copy_goes_with_it_and_git_still_prints_it(
    history, tmp_path, capfd
):
    added = {"src/nuikit/latest.py": '"""Latest run."""\n'}
    project = made_from_old_release(history, tmp_path / "old", files=added)

    update(project, trust=True)

    assert not (project / "src" / "nuikit").exists()
    assert "git show HEAD:<path>" in capfd.readouterr().out
    assert "Latest run" in sh(project, "git", "show", "HEAD:src/nuikit/latest.py")


def test_update_keeps_files_in_copies_that_git_ignores_and_names_them(
    history, tmp_path, capfd
):
    project = made_from_old_release(history, tmp_path / "old")
    ignored = {
        "src/nuikit/.env": "TOKEN=only-here\n",
        "src/nuikit/scratch/notes.md": "Only here.\n",
        "tests/nuikit/__pycache__/test_config.pyc": "",
    }
    write(project, ignored)
    # Git lists a nested repo it ignores as one folder, not file by file.
    sh(project / "src" / "nuikit" / "scratch", "git", "init", "-q")
    with (project / ".git" / "info" / "exclude").open("a", encoding="utf-8") as file:
        file.write("src/nuikit/scratch/\n")

    update(project, trust=True)

    left = sorted(
        str(path.relative_to(project))
        for folder in ("src/nuikit", "tests/nuikit")
        for path in (project / folder).rglob("*")
        if ".git" not in path.parts
    )
    assert left == [
        "src/nuikit/.env",
        "src/nuikit/scratch",
        "src/nuikit/scratch/notes.md",
    ]
    assert (project / "src" / "nuikit" / "scratch" / ".git" / "HEAD").is_file()
    assert (
        "kept in src/nuikit, since git ignores them: "
        "src/nuikit/.env, src/nuikit/scratch"
    ) in capfd.readouterr().out


def test_update_unlinks_copy_that_is_symlink_and_leaves_its_target_alone(
    history, tmp_path
):
    target = tmp_path / "checkout"
    write(target, {"wip.py": '"""Work in progress."""\n'})
    project = render(history, tmp_path / "old", vcs_ref=OLD_RELEASE, profile="rnd")
    shutil.rmtree(project / "src" / "nuikit")
    (project / "src" / "nuikit").symlink_to(target)
    (project / "tests" / "nuikit" / "linked").symlink_to(target)
    commit(project, "chore: start project")

    update(project, trust=True)

    assert not (project / "src" / "nuikit").exists(follow_symlinks=False)
    assert [path.name for path in target.iterdir()] == ["wip.py"]
    assert (target / "wip.py").read_text(encoding="utf-8") == (
        '"""Work in progress."""\n'
    )


def test_update_names_copy_that_is_broken_symlink_before_it_goes(
    history, tmp_path, capfd
):
    project = render(history, tmp_path / "old", vcs_ref=OLD_RELEASE, profile="rnd")
    (project / "CONVENTIONS.md").unlink()
    (project / "CONVENTIONS.md").symlink_to(tmp_path / "nowhere")
    commit(project, "chore: start project")

    update(project, trust=True)

    notice = next(
        line
        for line in capfd.readouterr().out.splitlines()
        if line.startswith("1.0.0 removes")
    )
    assert "CONVENTIONS.md" in notice
    assert not (project / "CONVENTIONS.md").exists(follow_symlinks=False)


def test_update_from_first_release_removes_core_copies_of_project_that_ran(
    history, tmp_path, capfd
):
    project = made_from_old_release(history, tmp_path / "first", release=FIRST_RELEASE)
    write(project, {"src/demo/core/__pycache__/paths.pyc": ""})

    update(project, trust=True)

    left = [
        path
        for path in ("src/demo/core", "tests/demo/core")
        if (project / path).exists()
    ]
    assert left == []
    assert "src/demo/core, tests/demo/core, local edits" in capfd.readouterr().out


def test_update_leaves_core_package_that_later_project_wrote_itself(
    history, tmp_path, capfd
):
    own = {"src/demo/core/__init__.py": '"""Scheduling core."""\n'}
    project = made_from_old_release(history, tmp_path / "old", files=own)

    update(project, trust=True)

    assert (project / "src" / "demo" / "core" / "__init__.py").is_file()
    assert "src/demo/core" not in capfd.readouterr().out


def test_update_of_project_that_names_old_repo_conflicts_in_uv_sources_only(
    history, tmp_path
):
    project = render(history, tmp_path / "old", vcs_ref=OLD_RELEASE, profile="rnd")
    pyproject = project / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    named = re.sub(r"^conventions-hooks = .*$", OLD_HOOKS_SOURCE, text, flags=re.M)
    pyproject.write_text(named, encoding="utf-8")
    commit(project, "chore: start project")

    update(project, trust=True)

    unmerged = sh(project, "git", "diff", "--name-only", "--diff-filter=U").split()
    merged = pyproject.read_text(encoding="utf-8")
    theirs = merged.split("=======\n")[1].split(">>>>>>> after updating")[0]
    assert unmerged == ["pyproject.toml"]
    assert merged.count("<<<<<<< before updating") == 1
    assert [line.split(" = ")[0] for line in theirs.splitlines()[1:]] == [
        "nuikit",
        "conventions-hooks",
    ]


def test_upgrade_notes_name_both_lines_that_point_old_project_at_this_repo(
    pytestconfig,
):
    notes = (pytestconfig.rootpath / "UPGRADING.md").read_text(encoding="utf-8")

    named = ["`_src_path`", "`conventions-hooks`", "`uv lock`", '"after updating"']
    assert [name for name in named if name not in notes] == []


def test_update_from_old_release_leaves_example_out(history, tmp_path):
    project = made_from_old_release(history, tmp_path / "old")

    update(project, trust=True)

    present = [path for path in EXAMPLE if (project / path).exists()]
    assert (answers_of(project)["example"], present) == (False, [])


def test_project_updated_from_old_release_passes_make_check(history, sources, tmp_path):
    project = made_from_old_release(history, tmp_path / "old")

    update(project, trust=True, **sources)

    sh(project, "uv", "sync")
    sh(project, "make", "check")


@pytest.mark.parametrize(
    ("project_name", "package"),
    [
        (LONGEST_NAME + "x", LONGEST_NAME.replace("-", "_") + "x"),
        ("helpers", "helpers"),
        ("p" * 51, "demo"),
        ("requests", "requests"),
        ("lab-", "lab_"),
    ],
    ids=["long-package", "vague", "long-project", "dependency", "trailing-dash"],
)
def test_update_keeps_name_that_new_project_could_not_take(
    history, tmp_path, project_name, package
):
    # In a folder of another name: copier drops an answer its validator refuses and
    # would take the folder's name instead.
    names = {"project_name": project_name, "package": package}
    project = made_from_old_release(history, tmp_path / "old", **names)

    update(project, trust=True)

    answers = answers_of(project)
    kept = {question: answers[question] for question in names}
    assert (answers["_commit"], kept) == ("v999.0.0", names)


@pytest.mark.parametrize("profile", ["uni", "lab"])
def test_update_of_uni_or_lab_project_is_refused_and_changes_nothing(
    history, tmp_path, capfd, profile
):
    project = made_from_old_release(history, tmp_path / "old", profile=profile)

    with pytest.raises(TaskError):
        update(project, trust=True)

    assert sh(project, "git", "status", "--porcelain") == ""
    assert f"has no {profile} profile" in capfd.readouterr().err


def test_update_across_migration_stops_until_it_is_trusted(history, tmp_path):
    project = made_from_old_release(history, tmp_path / "old")

    with pytest.raises(UnsafeTemplateError, match="--trust"):
        update(project)

    assert sh(project, "git", "status", "--porcelain") == ""


def test_update_within_release_needs_no_trust_and_removes_example_domain(
    releases, tmp_path
):
    project = tmp_path / "made"
    render(releases, project)
    commit(project, "chore: start project")

    update(project, example=False)

    config = (project / "src" / "demo" / "config.py").read_text(encoding="utf-8")
    assert ([p for p in EXAMPLE if (project / p).exists()], "signal" in config) == (
        [],
        False,
    )
