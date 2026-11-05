# rnd-template

A [copier](https://copier.readthedocs.io/) template for research and development projects: tools, pipelines and
training code, built as one package on [nuikit](https://github.com/nuinashco/nuikit), with Hydra + pydantic configs,
families of items, run directories, structlog, attrs, pyright and import-linter. A new project starts opted in to the
[nuinashco conventions](https://github.com/nuinashco/conventions): their checks run in pre-commit and CI, and their
Claude Code plugins are enabled in `.claude/settings.json`.

## Start a project

```bash
uvx copier copy --trust gh:nuinashco/rnd-template my-project
cd my-project
git init && make setup    # uv sync + pre-commit and commit-msg hooks
make check                # ruff, import contracts, pyright, pytest
make github               # once the GitHub repo exists: squash-merge settings (GIT-3)
```

Copier asks for the project name, the import package, the minimum Python (default 3.14), whether runs can mirror to
Weights & Biases, and whether to include the example domain; `--defaults` accepts every default. The example is a
small `signals` family and a `stats` domain wired into `<cli>-run`: it shows each pattern once, and new code copies its
shape. Its CONTRIBUTING.md says how to drop it once the first real family exists.

In Claude Code, trust the project folder and install the `conventions` and `nuikit` plugins it offers. Once per
machine, the marketplace that holds them may need adding first: `/plugin marketplace add nuinashco/conventions`.

## Update a project

Generated projects record the template version in `.copier-answers.yml`. From the project root, with a clean working
tree:

```bash
uvx copier update --trust
```

Copier merges template changes with local edits and marks conflicts inline, between `<<<<<<< before updating` and
`>>>>>>> after updating`. `--trust` lets the template's migrations run: updating across 1.0.0 deletes the copies that
earlier versions put in each project (`src/nuikit/`, `tests/nuikit/`, `CONVENTIONS.md`, `.claude/agents/`), since
nuikit is now a dependency and the conventions arrive through the plugins. For those projects the new `example`
question defaults to no, so the update adds no example domain to them. Then run `uv sync` and `make check`.

## What lives where

| repo | holds | rule IDs |
|---|---|---|
| this one | the template in `template/`, its questions and migrations in `copier.yml` | LAY-4, LAY-7, ENV-1 to ENV-3, TST-5, RUN-3 to RUN-7, TOOL-3 |
| [nuinashco/nuikit](https://github.com/nuinashco/nuikit) | the library projects depend on (config schemas, generated YAML, families, errors, logging, runs, seeding) and its `nuikit` Claude Code plugin; [docs/guide.md](https://github.com/nuinashco/nuikit/blob/main/docs/guide.md) | FAM, CFG, ERR-1, ERR-2, LOG-1, LOG-3, RUN-1, RUN-2 |
| [nuinashco/conventions](https://github.com/nuinashco/conventions) | the rules for every repo ([GUIDE.md](https://github.com/nuinashco/conventions/blob/main/GUIDE.md)), the `conventions-hooks` checks, the `conventions` plugin and the `nuinashco` marketplace | LAY-1 to LAY-3, LAY-5, LAY-6, ARC, TYP, STY, DOC, ERR-3 to ERR-6, LOG-2, LOG-4, LOG-5, TST, RDOC, GIT, TOOL |

This template's own rules ship with every project as path-scoped Claude Code rules, which Claude loads when it works
on the files they cover: [layout.md](template/.claude/rules/layout.md.jinja) (LAY-4, LAY-7, ENV-1 to ENV-3, TOOL-3
and the project's import layers), [runs.md](template/.claude/rules/runs.md.jinja) (RUN-3 to RUN-7) and
[tests.md](template/.claude/rules/tests.md) (TST-5). They have the same shape as the other repos' rules: a
`### <ID> <LEVEL>` heading, the rule, a *Why* where there is one, and a final *Check*.

`[tool.uv.sources]` pins both dependencies to release tags, `nuikit` and `conventions-hooks` at `v0.1.0`; a template
release that moves a pin reaches projects with `copier update`.

## Decisions

The choices behind the project layout; those behind the library and the general rules are in the other two repos.

| topic | decision | alternatives | why |
|---|---|---|---|
| shared machinery | `nuikit`, a dependency pinned to a tag | copied into every project by the template (before 1.0.0) | one source with its own tests and releases; a fix reaches a project as a pin change, and no copy drifts |
| rules in a project | path-scoped `.claude/rules/` for the template's rules, plugins for the rest | a vendored copy of the whole guide | Claude loads only the rules for the files it touches; a new general rule reaches every project without `copier update` |
| CLI | Hydra for config-heavy commands, click for utilities | Hydra only; click wrapping Hydra; typer | each fits its job |
| entry points | by lifecycle: workflow commands in `cli/`, one-offs in `scripts/` | by task type (data prep is a script); `scripts/` for everything; `cli/` only | commands get in-process tests and the layer check; one-offs stay out of the package; a task type says nothing about how often it runs |
| example domain | rendered by default, deleted once real code exists | an empty skeleton; examples only in docs | new code copies working, checked code; `make check` covers the example in every project |

## Change the template

Edit `template/` and `copier.yml`, then run the tests: they render three variants (the defaults; Python 3.12 with
W&B; no example), and in each run `make check`, the run command, `<cli>-configs --check`, `check-comments` and
`check-conventions` on every `.py` file, and check the Claude settings, the protected files and the rules' shape.
They also update a project across 1.0.0 to test the migration. Generated projects install nuikit and
conventions-hooks from local checkouts:

```bash
NUIKIT_PATH=~/src/nuikit CONVENTIONS_PATH=~/src/conventions make test
```

Without the two variables, the tests that install a project are skipped and say why. CI checks out both repos at
`main` next to this one. Commit, then tag `vMAJOR.MINOR.PATCH` so projects can `copier update`; a change that renames
a question or removes a file projects already have needs a migration in `copier.yml`.

## Known issues

- Python 3.14 needs `hydra-core>=1.4.0rc1`, a pre-release, because 1.3.x crashes on 3.14. Move the pin to 1.4.0 once
  it ships.
