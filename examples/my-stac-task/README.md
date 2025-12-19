# My STAC Task

**`my-stac-task`** is a fully functioning STAC task that can be copied locally for development and testing.  It follows best practices for building a STAC task to run in a cloud-deployed environment or locally via its command line interface.  `my-stac-task` is intended to help minimize time spent on repository set-up and configuration so that users can focus on custom business logic.

This document describes how to initialize a local code repository and provides some background on `stac-task` and Cirrus payloads.

## What do you need to know?

Users should have some basic familiarity with [SpatioTemporal Asset Catalog (STAC)](https://stacspec.org/) concepts as well as the [specification/schemas for STAC objects](https://github.com/radiantearth/stac-spec).

STAC tasks are generally assumed (but not required) to be part of a [Cirrus workflow](https://github.com/cirrus-geo/cirrus-geo).  The [Cirrus Docs](https://cirrus-geo.github.io/cirrus-geo/v0.15.4/index.html) provide in-depth info - the section on the [Cirrus Process Payload](https://cirrus-geo.github.io/cirrus-geo/v0.15.4/cirrus/30_payload.html) is particularly relevant since that is the data structure for STAC task inputs.

`my-stac-task` is set-up for and intended to be managed with [uv](https://docs.astral.sh/uv/).  Users should [install uv](https://docs.astral.sh/uv/getting-started/installation/) and see the specific initialization guidance below.

## Building the STAC task scaffolding

`my-stac-task` lives in the `examples/` section of the `stac-task` code repository. To generate the scaffolding for a STAC task, `my-stac-task` should first be copied to a local directory; second, task naming needs to be adjusted to suit user needs.  There are a few ways to do that - here are two:

### via GitHub Content Downloader

If you have `uv` installed, you can use the command below to set-up a task - `uv` will use the GitHub Content Downloader library to draw directly from the `stac-task` public repository and place the files locally.

1. Navigate to the location where you want to put your task
2. Run the following command (you will probably want to rename the destination directory, _i.e._ `my-stac-task` to your project name):
```bash
uvx --from github-content-downloader ghcd https://github.com/stac-utils/stac-task/tree/main/examples/my-stac-task && mv downloaded_files my-stac-task
```

### via `stac-task` clone

An alternative method is just to clone `stac-task` locally and `examples/my-stac-task` to the desired location.

### Initialize the STAC task project

Once `uv` is installed, the project's environment can be initialized as follows:
```bash
# Create and activate the local virtual environment
uv venv
source .venv/bin/activate

# Install all dependencies (including dev dependencies)
uv sync --all-groups
```

Pre-commit and its dependencies can be installed and run:
```bash
# Pre-commit setup and run
uv run pre-commit install
uv run pre-commit run --all-files

# Lint, format, and type-check
uv run ruff check .
uv run ruff format .
uv run mypy src
```

Finally, run the tests:
```bash
uv run pytest -vv
```
The `tests/test_task.py` module contains test code to iterate through the input payloads in `fixtures`, which contains a series of input and payload files, each pair in it's own folder. For expected errors in tests an `exception.txt` file is provided intead of an output payload.

### Run the task

`my-stac-task` can be run from the command line using the `stac-task` CLI (from the root directory):
```bash
uv run my-stac-task run tests/fixtures/payloads/success/payload1/in.json --local
```
Using the `--local` option will store all output in a local folder called `local-output` and will not try to upload the data files to s3.  To re-direct local outputs to another location use the `--output` option to specify a different path.

For help with the `stac-task` CLI, run:
```bash
uv run my-stac-task run -h
```

## Template Usage

This example STAC task is intended to be used as a template.
- Update `pyproject.toml` with the project name, authors, description, dependencies, etc.
- Rename the folder `src/my_stac_task` to match the project name
- Add test payload fixtures under `tests/fixtures`
- Add code to `src/<project-name>/task.py` and add supporting files as needed
- Update the Repostitory URL in CHANGELOG.md and keep it up to date with versions

### AI Prompt for Project Set-up

Rename the `my-stac-task` project to <my-new-project>.
Find and replace all instances of `my-stac-task`:
* replace all kebab case with the new project name (_e.g._ project and task references)
* replace all camel case with a camel cased version of the new project name (_e.g._ `task.MyStacTask` references)
* replace all snake case with a snake cased version of the new project name (_e.g._ source code directory)

Validate the results of name changing:
* Ensure all tests pass by running `uv run pytest -vv`.  Investigate the cause of any test failure and fix any project name references that are incorrect.
* Ensure the CLI still runs locally using this payload: `tests/fixtures/payloads/success/payload1/in.json` and the `--local` argument.  Review any CLI failure and fix any project name references.

# Versions and Releases

![CalVer:YYYY.0M.0D\_MICRO](https://img.shields.io/badge/CalVer-YYYY.0M.0D__MICRO-00aa00.svg)

This project uses CalVer for versioning releases.  The format is specified as
`YYYY.0M.0D_MICRO`, where the tokens are:

| token | description                     | example(s)             |
|-------|---------------------------------|------------------------|
| YYYY  | the full year                   | 2006, 2016, 2112       |
| 0M    | the zero-padded month           | 01, 02 ... 11, 12      |
| 0D    | the zero-padded day of month    | 01, 02 ... 30, 31      |
| MICRO | (optional) free form, as needed | alpha, rc0, post0, ... |
