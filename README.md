# rnd-template

A [copier](https://copier.readthedocs.io/) template that starts a Python research or development project with the
groundwork done: one package built on [nuikit](https://github.com/nuinashco/nuikit), Hydra configs validated by
pydantic, a folder per run, tests, type checks, and the
[nuinashco conventions](https://github.com/nuinashco/conventions) with their checks and Claude Code plugins.

It is for tools, pipelines and training code that run many times with different settings.

## Start a project

You need [uv](https://docs.astral.sh/uv/) and git.

```bash
uvx copier copy gh:nuinashco/rnd-template my-project
cd my-project
git init && make setup    # install the dependencies and the git hooks
make check                # ruff, the conventions checks, import layers, pyright, pytest
```

Copier asks for the project name, the import package, the minimum Python (3.14 by default), whether runs can mirror
to Weights & Biases, and whether to include the example. `--defaults` accepts every default.

The new project already runs:

```bash
uv run my-project-run run_name=first    # writes runs/first/: config.yaml, run.json, summary.json
uv run my-project-run signal=constant   # any setting can be overridden on the command line
```

## What you get

```text
my-project/
  src/my_project/   the package: cli/ for commands, config.py for settings, paths.py, the example
  configs/          Hydra configs; the files that say "Generated" mirror the settings in code
  tests/            mirrors src/, plus checks of the whole repo
  Makefile          setup, check, format, configs; `make help` lists them
  README.md         for users; CONTRIBUTING.md for contributors; AGENTS.md for coding agents
  .claude/          turns on the conventions and nuikit plugins, and holds this template's rules
```

The example is a small family of signals and a statistics module wired into the run command. It shows each pattern
once, so new code can copy its shape. The project's CONTRIBUTING.md says how to remove it once real code exists.

In Claude Code, trust the project folder and install the `conventions` and `nuikit` plugins it offers. On a machine
that has never used them, add their marketplace first: `/plugin marketplace add nuinashco/conventions`.

## Update a project

A project remembers the template release it came from in `.copier-answers.yml`. To pull in a newer one, run this
from the project root with a clean working tree:

```bash
uvx copier update --trust
```

Copier merges the template's changes with yours and marks conflicts inline, between `<<<<<<< before updating` and
`>>>>>>> after updating`. `--trust` lets the template's migrations run. Afterwards run `uv sync` and `make check`.

### From a release before 1.0.0

- **`uni` and `lab` projects stay where they are.** Since 1.0.0 the template holds the R&D project only, so the
  update stops in a project made with another profile and changes nothing.
- **Point the project at this repo first.** Its `.copier-answers.yml` names nuinashco/conventions, where the template
  used to live. Set `_src_path: gh:nuinashco/rnd-template` in that file by hand, commit, then update.
- **The update deletes the copies old releases put in the project:** `src/nuikit/`, `tests/nuikit/`,
  `CONVENTIONS.md` and the two subagents in `.claude/agents/`. nuikit is a dependency now, and the rules come with
  the plugins. Local edits to those files go too; `git checkout HEAD -- <path>` brings one back before you commit.
- **No example is added** to a project that already exists.

## Related repos

| repo | holds |
|---|---|
| [nuikit](https://github.com/nuinashco/nuikit) | The library a project imports: config schemas, generated YAML, families, errors, logging, runs, seeding. |
| [conventions](https://github.com/nuinashco/conventions) | The rules, the checks that enforce them and the Claude Code plugins. |

A project pins a release tag of each under `[tool.uv.sources]` in its `pyproject.toml`. A template release moves the
pins, and `copier update` brings them to the project.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) covers the layout of this repo, its tests, the decisions behind the project and
how to release.
