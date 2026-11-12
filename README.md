# rnd-template

A [copier](https://copier.readthedocs.io/) template that starts a Python research or development project with the
groundwork done: one package built on [nuikit](https://github.com/nuinashco/nuikit), Hydra configs validated by
pydantic, a folder per run, tests, type checks, and the
[nuinashco conventions](https://github.com/nuinashco/conventions) with their checks and Claude Code plugins.

It is for tools, pipelines and training code that run many times with different settings.

## Start a project

You need [uv](https://docs.astral.sh/uv/), git and make.

```bash
uvx copier copy gh:nuinashco/rnd-template my-project
cd my-project
git init -b main
make setup
make check
```

Copier asks for the project name (the folder's name by default), the import package, a description, the author, the
minimum Python (3.14 by default), whether runs can mirror to Weights & Biases, and whether to include the example.
`--defaults` accepts every default, the template author's name among them, so pass yours with it:
`-d author_name=... -d author_email=...`. `make setup` installs the dependencies and the git hooks; `make check`
runs what CI runs: ruff, the conventions checks, the import layers, pyright and pytest. Commit everything it
leaves, `uv.lock` included: CI installs from it.

The new project already runs:

```bash
uv run my-project-run run_name=first
uv run my-project-run signal=constant
```

The first command writes `runs/first/` with `config.yaml`, `run.json` and `summary.json`. The second overrides a
setting, as any `key=value` on the command line does.

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

The project's `.claude/settings.json` turns on two Claude Code plugins, `conventions` and `nuikit`. Install them
once per machine:

```text
/plugin marketplace add nuinashco/conventions
/plugin install conventions@nuinashco
/plugin install nuikit@nuinashco
```

A cloud session loads no plugins; there the project's AGENTS.md sends Claude to the rules instead.

## Update a project

A project remembers the template release it came from in `.copier-answers.yml`. To pull in a newer one, run this
from the project root with a clean working tree:

```bash
uvx copier update
```

Copier merges the template's changes with yours and marks conflicts inline, between `<<<<<<< before updating` and
`>>>>>>> after updating`. Afterwards run `uv sync` and `make check`. A release that brings a migration, a script
that changes the project, needs `uvx copier update --trust`: without it copier stops and says so.

A project made from a release before 1.0.0 needs two edits first, and the update removes what those releases
copied into it: [UPGRADING.md](UPGRADING.md) has the steps.

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
