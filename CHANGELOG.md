# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- ([#72]) Given that `_get_file` is part of the `AsyncFileSystem` spec, this
  adds the synchronous `get_file` as a way to retrieve files if `_get_file` is
  not found.

## [v0.3.0] - 2023-12-20

### Changed

- handler now explicitly calls performs workdir cleanup
- workdir cleanup is correctly defensive and logs errors

## [v0.2.0] - 2023-11-16

### Changed

- Ensure `workdir` is an absolute path
  ([#54](https://github.com/stac-utils/stac-task/pull/51)).
- When a `workdir` is set for a `Task` the `workdir` will no longer be removed
  by default ([#51](https://github.com/stac-utils/stac-task/pull/51)). That is,
  the `save_workdir` argument to `Task` constructor now defaults to `None`, and
  if left as `None` the default behavior is now conditional on whether or not a
      `workdir` is specified.

  - If `workdir` is `None`, a temp directory will be created and `save_workdir`
    will default to `False` (remove working directory).
  - If a `workdir` is specified, then `save_workdir` will default to `True`
    (keep working directory).

  In either case, an explicit `True` or `False` value for `save_workdir` will
  take precedence.

## [v0.1.1] - 2023-07-12

### Fixed

- Typing ([#11](https://github.com/stac-utils/stac-task/pull/11), [#25](https://github.com/stac-utils/stac-task/pull/25))
- Removed console scripts ([#18](https://github.com/stac-utils/stac-task/pull/18))

## [v0.1.0] - 2022-10-31

Initial release.

<!-- [Unreleased]: <https://github.com/stac-utils/stac-task/compare/v0.1.1...main> -->
[v0.3.0]: <https://github.com/stac-utils/stac-task/compare/v0.2.0...v0.3.0>
[v0.2.0]: <https://github.com/stac-utils/stac-task/compare/v0.1.1...v0.2.0>
[v0.1.1]: <https://github.com/stac-utils/stac-task/compare/v0.1.0...v0.1.1>
[v0.1.0]: <https://github.com/stac-utils/stac-task/tree/v0.1.0>
