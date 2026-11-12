# Upgrading a project to 1.0.0

For a project made from a release before 1.0.0 (`v0.1.0` to `v0.3.4`). Later updates need none of this:
[README.md](README.md#update-a-project).

## 1. Point the project at this repo

The old releases lived in nuinashco/conventions and moved here with their tags. Until a project points at this
repo, `make lab` and a fresh `uv sync`, CI's included, cannot find its release. Replace `nuinashco/conventions`
with `nuinashco/rnd-template` in two lines:

- `_src_path` in `.copier-answers.yml`
- `conventions-hooks` in `pyproject.toml`

Then run `uv lock` and commit. A `uni` or `lab` project is done here: since 1.0.0 the template holds the R&D
project only, so such a project stays on its release, and the update below stops in it and changes nothing.

## 2. Update

```bash
uvx copier update --trust
```

`--trust` lets the migration of 1.0.0 run. If the `pyproject.toml` line was left as it was, the update marks one
conflict under `[tool.uv.sources]`: keep the "after updating" side. Then run `uv sync` and `make check`.

## What changes

- **The copies old releases put in the project go:** `src/nuikit/`, `tests/nuikit/`, `CONVENTIONS.md` and the two
  subagents in `.claude/agents/`. nuikit is a dependency now, and the rules come with the plugins. Local edits to
  those files go too: until you commit the update, `git show HEAD:<path>` prints one, so you can move the change
  into your own package. Files git ignores in those folders stay, and the update names them.
- **A project from v0.1.0** holds its copy as `src/<package>/core/`, with its tests in `tests/<package>/core/`:
  both go as well. Imports of `<package>.core` become imports of `nuikit`, except `<package>.core.paths`, which is
  `<package>.paths` now.
- **`data`, `runs`, `outputs`, `multirun`, `build` and `dist` are ignored at the top level only.** A folder of that
  name under `src/` or `tests/` shows up in `git status` after the update: commit it, or ignore it yourself.
- **No example is added** to a project that already exists.
- **The project keeps its names.** A package name that a new project could not take, because it is longer than 27
  characters or as vague as `utils`, stays as it is.
