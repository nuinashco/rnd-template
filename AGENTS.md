# AGENTS.md

This repo is a copier template for R&D projects built on nuikit. `copier.yml` holds the questions and migrations;
`template/` is the project it renders. The rules for every repo live in nuinashco/conventions and reach Claude through
the `conventions` plugin; nuikit's rules come with the `nuikit` plugin. This template owns LAY-4, LAY-7, ENV-1 to
ENV-3, TST-5, RUN-3 to RUN-7 and TOOL-3, written in `template/.claude/rules/`. More: [CONTRIBUTING.md](CONTRIBUTING.md).

## Commands

```bash
make lint     # ruff, check-comments and check-conventions on tests/
make test     # render every variant, run its make check, commands and hooks; update a real v0.3.4 project
NUIKIT_PATH=../nuikit CONVENTIONS_PATH=../conventions make lint test    # the same against local checkouts
```

The tests install each rendered project with `uv sync` (about a minute, needs network). Without the two paths a
project installs the nuikit and conventions releases `copier.yml` pins, as a user's does; with them, the checkouts as
they are on disk. The update tests need the release tags: `git fetch --tags`.

## Layout

```text
copier.yml        questions, hidden answers (nuikit_source, hooks_source), derived names, _migrations
template/         the generated project; *.jinja files are rendered, `{% if example %}` names render only with the example
  .claude/        settings.json (the plugins, no hooks) and rules/ (this template's rules, path-scoped)
tests/            test_template.py: three variants, updates from the v0.3.4 release, removing the example
README.md         starting and updating a project
CONTRIBUTING.md   what lives in the other repos, tests, releases, decisions
```

## Working here

- Generated projects follow the conventions, so template code is held to them: attrs classes, one-line module
  docstrings, comments only for what code can't say, keyword-only options, ASCII `.py`, sentence-named tests with
  fakes. Every render runs its own `make check`, which includes `check-comments` and `check-conventions`.
- Every variant must render and pass: defaults, Python 3.12 with `use_wandb`, and `example=false`. Code under
  `{% if example %}` must leave nothing behind when the example is off, including import layers and docs.
- Generated YAML in `template/configs/` must match what nuikit's `configgen` writes; render, run `make configs`
  and copy the output back rather than writing it by hand.
- Rules in `template/.claude/rules/` keep the shared shape: `### <ID> <LEVEL>`, the rule, `*Why:*` where there is
  one, and a final `*Check:*` paragraph. Keep IDs; never reuse a retired one. Keep them short: Claude loads them.
- `copier update` must keep working on existing projects: no renamed questions, and a migration for every file a
  release stops shipping. Releases are tags `vMAJOR.MINOR.PATCH`.
- Change nuikit or the conventions in their own repos; this one only pins their release tags, in `copier.yml`
  and, for `make lint`, the conventions tag in the `Makefile`; a test keeps the two equal.
- Commits are one line, Conventional Commits, lowercase imperative subject, no articles, no body (GIT-1, GIT-2).
