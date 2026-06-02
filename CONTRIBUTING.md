# Contributing to Eventum

Thanks for your interest in improving Eventum. This document covers how to report issues, set up a development environment, and submit changes.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- Report bugs and request features through [issues](https://github.com/eventum-generator/eventum/issues).
- Improve the [documentation](https://eventum.run) (the docs site lives in a separate repository).
- Share or improve ready-to-use generators (content packs).
- Fix bugs or implement features and open a pull request.

## Questions and discussions

For usage questions, ideas, and open-ended discussion, use [GitHub Discussions](https://github.com/orgs/eventum-generator/discussions) rather than the issue tracker. Issues are reserved for actionable bug reports and feature requests.

## Reporting bugs and requesting features

Open an issue and pick the matching template. The forms ask for the information needed to act on the report, so please fill them in completely - especially the Eventum version, how you run it, and a minimal config or template that reproduces the problem.

Do not report security vulnerabilities through public issues. See [SECURITY.md](SECURITY.md) for the private reporting process.

## Development setup

### Prerequisites

- [Git](https://git-scm.com/)
- [Python](https://www.python.org/) 3.14 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management and running tools
- For the Studio UI: [Node.js](https://nodejs.org/) (current LTS) and [pnpm](https://pnpm.io/)
- Optionally, [Docker](https://www.docker.com/) to run the full stack in a container

### Backend

```bash
git clone https://github.com/eventum-generator/eventum.git
cd eventum
uv sync
```

`uv sync` installs the project together with the `dev` dependency group (pytest, ruff, mypy, and friends).

Run a single generator or the full application:

```bash
uv run eventum generate --path generator.yml --id dev --live-mode true
uv run eventum run -c config/eventum.yml
```

Reference `eventum.yml` and `startup.yml` configurations live in `config/`.

### Frontend (Studio UI)

The web UI lives in `eventum/ui/`:

```bash
cd eventum/ui
pnpm install
pnpm dev      # start the dev server
pnpm build    # type-check (tsc) and build
```

## Making a change

### Branching

Eventum follows the git-flow model. Branch off `develop`, never off `master`:

```bash
git switch develop
git switch -c feat/<short-description>
```

Pull requests target `develop`. `master` holds released versions only.

### Tests

Every feature or bug fix ships with tests. Unit tests are co-located with the code they cover, under `<package>/tests/test_<name>.py`. Integration and performance suites live under the top-level `tests/` directory.

### Checks

Before opening a pull request, run the same checks CI runs.

Backend:

```bash
uv run ruff format        # format
uv run ruff check         # lint
uv run mypy eventum/      # type-check
uv run pytest             # tests
```

Frontend (from `eventum/ui/`):

```bash
pnpm lint                 # ESLint
pnpm build                # tsc + Vite build
```

Run all backend tools through `uv run` to use the project environment; do not invoke `python`, `pytest`, `ruff`, or `mypy` directly.

## Coding style

- Python: 79-character lines for code, 72 for docstrings; ASCII only in code, comments, and docstrings. Public interfaces carry full type hints and docstrings. `ruff` handles formatting and linting; `mypy` runs in standard mode.
- Use a single hyphen `-` in source code, not an em dash.
- Frontend: TypeScript checked by `tsc`, linted by ESLint, formatted by Prettier.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/). The scope must be a top-level package name: `plugins`, `core`, `api`, `ui`, `server`, `app`, `cli`, `logging`, `security`, or `utils`.

Examples:

```
feat(plugins): add module.rand.network.mac()
fix(core): size the write pool to concurrent writes
docs(cli): clarify --live-mode flag
```

## Opening a pull request

1. Make sure your branch is based on `develop` and targets `develop`.
2. Add or update tests and confirm all checks pass locally.
3. Fill in the pull request template, including a clear description and any related issue (`Closes #123`).
4. A maintainer will review your change. Address feedback by pushing follow-up commits to the same branch.

## License

By contributing, you agree that your contributions are licensed under the [Apache License 2.0](LICENSE), the same license that covers the project.
