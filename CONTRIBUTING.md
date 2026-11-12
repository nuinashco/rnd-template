# Contributing

How the template is built and how to change it. Using it: [README.md](README.md). Template code is held to the
[nuinashco conventions](https://github.com/nuinashco/conventions/blob/main/GUIDE.md) and to
[nuikit's guide](https://github.com/nuinashco/nuikit/blob/main/docs/guide.md), like the projects it renders.

## Repository layout

```text
copier.yml        the questions, the hidden answers (nuikit_source, hooks_source), derived names, _migrations
includes/         names.jinja: the names a project cannot take, as macros the name questions import
migrations/       scripts that `_migrations` run in a project during `copier update`
template/         the generated project; *.jinja files are rendered, `{% if example %}` names only with the example
  .claude/        settings.json (the plugins, no hooks) and rules/ (this template's rules, path-scoped)
tests/            test_template.py: three variants, awkward answers and names, updates from old releases
Makefile          lint and test
UPGRADING.md      the steps for a project made before 1.0.0
```

## What lives where

| repo | holds | rule IDs |
|---|---|---|
| this one | the template in `template/`, its questions and migrations in `copier.yml` | LAY-4, LAY-7, ENV-1 to ENV-3, TST-5, RUN-3 to RUN-7, TOOL-3 |
| [nuinashco/nuikit](https://github.com/nuinashco/nuikit) | the library projects depend on and its `nuikit` Claude Code plugin; [docs/guide.md](https://github.com/nuinashco/nuikit/blob/main/docs/guide.md) | FAM, CFG, ERR-1, ERR-2, LOG-1, LOG-3, RUN-1, RUN-2 |
| [nuinashco/conventions](https://github.com/nuinashco/conventions) | the rules for every repo ([GUIDE.md](https://github.com/nuinashco/conventions/blob/main/GUIDE.md)), the `conventions-hooks` checks, the `conventions` plugin and the `nuinashco` marketplace | LAY-1 to LAY-3, LAY-5, LAY-6, ARC, TYP, STY, DOC, ERR-3 to ERR-6, LOG-2, LOG-4, LOG-5, TST-1 to TST-4, TST-6 to TST-8, RDOC, GIT, TOOL-1, TOOL-2, TOOL-4 to TOOL-6 |

This template's own rules ship with every project as path-scoped Claude Code rules, which Claude loads when it works
on the files they cover: [layout.md](template/.claude/rules/layout.md.jinja) (LAY-4, LAY-7, ENV-1 to ENV-3, TOOL-3
and the project's import layers), [runs.md](template/.claude/rules/runs.md.jinja) (RUN-3 to RUN-7) and
[tests.md](template/.claude/rules/tests.md) (TST-5). They have the same shape as the other repos' rules: a
`### <ID> <LEVEL>` heading, the rule, a *Why* where there is one, and a final *Check*. Keep the IDs, and never reuse
a retired one.

## Changing the template

- Every variant must render and pass: the defaults, Python 3.12 with `use_wandb`, and `example=false`. Code under
  `{% if example %}` leaves nothing behind when the example is off, including import layers and docs.
- Generated YAML in `template/configs/` matches what nuikit's `configgen` writes: render a project, run
  `make configs` and copy the output back.
- `copier update` keeps working on existing projects: no renamed questions, a migration in `copier.yml` for
  every file a release stops shipping, and no new refusal of an answer a project already has. The name questions
  show how: a check that only style asks for is skipped when `_copier_conf.overwrite` is set, as it is in an
  update.
- A dependency added to `template/pyproject.toml.jinja` adds its import and distribution names to `installed`
  in `includes/names.jinja`; a test names the ones that are missing.
- Change nuikit or the conventions in their own repos. This one only pins their release tags: both in `copier.yml`
  and, for `make lint`, the conventions tag in the `Makefile`.

## Tests

```bash
make lint
make test
```

`make lint` runs ruff, `check-comments` and `check-conventions` on `tests/` and `migrations/`. `make test` takes
about two minutes and needs network. The tests render the three variants and, in each project, run `make check`, the
run command and `<cli>-configs --check`, then check the Claude settings, the protected files and the shape of the
rules. They also render projects from the `v0.3.4` and `v0.1.0` tags of a local clone and update them to the working
tree: the copies go, a `uni` or `lab` project is refused untouched, and `make check` passes in a project updated from
`v0.3.4`. That needs the release tags, so fetch them (`git fetch --tags`). Such a project names its
`conventions-hooks` source as a local path; one test rewrites the line to what a project made on GitHub carries.

Each project installs nuikit and conventions-hooks at the releases `copier.yml` pins, which is what a user gets. To
test against checkouts instead, as they are on disk:

```bash
NUIKIT_PATH=~/src/nuikit CONVENTIONS_PATH=~/src/conventions make lint test
```

CI checks out both repos at `main` and tests against those.

## Release

1. To take a new nuikit or conventions release, move its tag in `copier.yml`, and the conventions tag in the
   `Makefile` with it. The release must exist first: projects install it.
2. Merge, then tag `main` once CI passes: `git tag v1.0.1 && git push origin v1.0.1`. Projects take it with
   `copier update`. A release that adds a migration gets the version the migration names.

## Decisions

The choices behind the project layout; those behind the library and the general rules are in the other two repos.

| topic | decision | alternatives | why |
|---|---|---|---|
| shared machinery | `nuikit`, a dependency pinned to a tag | copied into every project by the template (before 1.0.0) | one source with its own tests and releases; a fix reaches a project as a pin change, and no copy drifts |
| rules in a project | path-scoped `.claude/rules/` for the template's rules, plugins for the rest | a vendored copy of the whole guide | Claude loads only the rules for the files it touches; a new general rule reaches every project without `copier update` |
| CLI | Hydra for config-heavy commands, click for utilities | Hydra only; click wrapping Hydra; typer | each fits its job |
| entry points | by lifecycle: workflow commands in `cli/`, one-offs in `scripts/` | by task type (data prep is a script); `scripts/` for everything; `cli/` only | commands get in-process tests and the layer check; one-offs stay out of the package; a task type says nothing about how often it runs |
| example domain | rendered by default, deleted once real code exists | an empty skeleton; examples only in docs | new code copies working, checked code; `make check` covers the example in every project |
| profiles | the R&D project only | `uni` and `lab` profiles next to it (before 1.0.0) | copier's update story assumes one template per repository; a `uni` or `lab` project stays on `v0.3.4` |

## Known issues

- Projects depend on `hydra-core>=1.4.0rc1`, a pre-release: Hydra 1.3 crashes on Python 3.14 and does not accept
  OmegaConf 2.4, which nuikit needs. Move the pin to 1.4.0 once it ships.

## Commits

Conventional Commits with the standard types (`feat fix docs refactor test build ci perf style chore revert`), an
optional scope, a lowercase imperative subject: one line, no articles, no body or trailers. Short-lived
`<type>/<slug>` branches, squash-merged, with the PR title as the commit.
