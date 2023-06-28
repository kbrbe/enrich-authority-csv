# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2023-06-28

As of this version, the tool can be installed via `pip` and can be used as a library and not only via the commandline.

### Added

- The possibility to install the tool via `pip` ([#7](https://github.com/kbrbe/enrich-authority-csv/issues/7)

### Changed

- The import of the lib module is no longer relative, this means to use the tool without installing it one has to set the `PYTHONPATH` environment variable, for example `export PYTHONPATH=/home/youruser/repo/enrich-authority-csv`

## [0.2.0] - 2023-06-23

In this version the name of the tool changed from `enrich-authority-csv-via-isni` to the more generic `enrich-authority-csv`.
Mainly because the script was generalized to handle more than just the ISNI SRU API based on a configuration file and new commandline arguments.

### Added

- The possibility to fill datafield gaps from other APIs via a configuration file ([#3](https://github.com/kbrbe/enrich-authority-csv/issues/3))

### Changed

- Due to the new features the commandline parameters have been adapted, see README file

### Fixed

- The progress bar had a wrong total and never reached 100%, this was fixed ([#2](https://github.com/kbrbe/enrich-authority-csv/issues/2))

## [0.1.0] - 2023-06-19

### Added

- Initial version of the script copied from a feature branch of https://github.com/kbrbe/beltrans-data-integration/

[0.1.0]: https://github.com/kbrbe/enrich-authority-csv/releases/tag/v0.1.0
[0.2.0]: https://github.com/kbrbe/enrich-authority-csv/compare/v0.1.0...v0.2.0
[0.2.0]: https://github.com/kbrbe/enrich-authority-csv/compare/v0.2.0...v0.3.0
