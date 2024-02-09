<!--
  formatted using prettier inside ./doc (see TG-1998):
  cd doc && yarn && yarn prettier --write --tab-width=4 ../CHANGELOG.md

  All lines with an heading of second level must match the following regex, with the captured match a valid PEP 440 version string :
      /^## \[(.*)\] − (?:(?:Unreleased)|(?:\d\d\d\d-\d\d-\d\d))$/
  Additionally the first one of these lines is updated or created by the script `version_management.py`, and its version must be the
  current version as declared in pyproject.toml
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [PEP 440 Versioning](https://peps.python.org/pep-0440/).

## [0.1.7.post.dev] − Unreleased

### Fixed

-   **Backends**
    -   Error while retrieving token from `Redis` cache if empty <!-- TG-2064 -->

## [0.1.7] − 2024-02-08

### Added

-   New Py-youwol documentation application **@youwol/py-youwol-doc** <!-- TG-1923, TG-1924, TG-1925, TG-1951, TG-1952, TG-1961 -->

### Changed

-   Improve authentication for HTTP clients <!-- TG-1874 -->
-   Improve error management during projects load <!-- TG-1878 -->
-   **Pipeline Typescript**:
    -   improve step custom views API <!-- TG-1862 -->
    -   use caret range for shared configuration dependencies <!-- TG-1912 -->
    -   upgrade shared configuration `^1.2.0` for latest dependencies: <!-- TG-1954, TG-1980 -->
        -   Typescript `^5.3.3`
        -   Jest `^29.5.11`
        -   ESlint `8.56.0`
        -   Prettier `^3.2.4`
-   **Docker images**:
    -   use Python 3.12 <!-- TG-1848, TG-1850 -->
    -   run as non-privileged user <!-- TG-1957 -->

### Fixed

-   Reduce verbosity in terminal when creating project <!-- TG-1735 -->
-   **Pipeline Typescript**:
    -   allow modifying dependency defined by pipeline using `template.py` <!-- TG-1911 -->
    -   format `src/test/fake.ts` <!-- TG-1706 -->
    -   pin `@types/node` to `18.19.9`
        for applications until [chokidar issue #1299](https://github.com/paulmillr/chokidar/issues/1299) is resolved <!-- TG-1983 -->

### Security

-   **Dependencies vulnerabilities**:
    -   [CVE-2023-26159] upgrade `follow-redirects` to 1.15.5 <!-- TG-1906 -->
    -   [CVE-2024-23334] upgrade `aiohttp` to 3.9.2 <!-- TG-1984 -->
    -   [CVE-2024-23829] upgrade `aiohttp` to 3.9.2 <!-- TG-1984 -->
    -   [CVE-2023-50782] upgrade `cryptography` to 42.0.2 <!-- TG-2049 -->
    -   [CVE-2024-24762] upgrade `fastapi` to 0.109.2, `starlette` to 0.36.3 <!-- TG-2047, TG-2048 -->

<!-- Not worthy of inclusion
TG-1881
TG-1889
TG-1949
TG-1960
TG-1962
TG-1963
TG-1981
TG-2021
TG-2057
TG-2058
TG-2059
-->

## [0.1.6] - 2023-12-18
