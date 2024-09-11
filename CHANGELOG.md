<!--
  formatted using prettier inside ./doc/front-app:
  $ cd doc/front-app && yarn && yarn prettier --write ../../CHANGELOG.md && cd ../..
  $ git diff CHANGELOG.md

  All lines with an heading of second level must match the following regex, with the captured match a valid PEP 440 version string :
      /^## \[(.*)\] − (?:(?:Unreleased)|(?:\d\d\d\d-\d\d-\d\d))$/
  Additionally the first one of these lines is updated or created by the script `version_management.py`, and its version must be the
  current version as declared in pyproject.toml
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [PEP 440 Versioning](https://peps.python.org/pep-0440/).

## [0.1.13.dev] − Unreleased

### Added

-  **yw_clients**:
  - Add new python package `yw_clients` in `/lib`. It provides HTTP clients and logs management to interact
    with YouWol's backends. <!-- TG-2480 -->

### Changed

- **Pipeline Python Backend**:
  -  Pipeline does not produce auto-generated `requirements.txt` anymore. <!-- TG-2459 -->

<!-- Not worthy of inclusion
TG-2474 : 💄 [pipelines] Improve styling of config. step views
TG-1461 : 💚 [release] allow installing local release in venv
TG-1462 : 💚 [release] push versions bump after publishing
TG-1464 : 👽️ [workflows] hidden files in uploaded config
TG-1467 : 💚 [release] Checkout with depth=3 for publishing
-->

## [0.1.12] − 2024-09-02

### Added

- **Pipeline TS**:
  - Add `DevServerStep` for projects producing applications. <!-- TG-2445 -->
- **ESM live servers**:
  - Add API to provide the ability to install ESM live servers dynamically. <!-- TG-2441 -->
- **Custom Backends**:
  - Custom backends now run within isolated partitions and can be dynamically configured during the build stage.
    <!-- TG-2389 -->
- **Pipeline Python Backend**:
  - `youwol` dependency minimal version no longer hard-coded, use the release version <!-- TG-2460 -->

### Changed

- Upgrade `GET:/co-lab` target from `@youwol/co-lab#^0.3.0` to `@youwol/co-lab#^0.5.0`. <!-- TG-2399 --> <!-- TG-2444 ->
- Upgrade dependency `requests` to 2.32.3
  because [previous version has been yanked](https://pypi.org/project/requests/2.32.1/) <!-- TG-2420 -->
- Increase the timeout (20 seconds) to wait for readiness of a custom backend. <!-- TG-2455 -->

### Fixed

- Resolved issues with fetching Pyodide resources when multiple Pyodide runtime versions are available within the
  py-youwol environment. <!-- TG-2416 -->
- Resolved an issue preventing retrieving the PID of a proxied ESM server from its port. <!-- TG-2456 -->

### Removed

- Dynamic generation of code documentation and associated `admin/system/documentation` endpoint have been removed.
  <!-- TG-2432 -->

### Security

- **Dependencies vulnerabilities**:
  - [GHSA-248v-346w-9cwc] Upgrade `certifi` to 2024.7.4 <!-- TG-2419 -->
  - [GHSA-jfmj-5v4g-7637] Upgrade `zipp` to 3.19.2 <!-- TG-2418 -->
  - [GHSA-cx63-2mw6-8hw5] Upgrade `setuptools` to 70.3.0 <!-- TG-2422 -->
  - [GHSA-jwhx-xcg6-8xhj] Upgrade `aiohttp` to 3.10.5 <!-- TG-2450 -->

<!-- Not worthy of inclusion
TG-2377 : Use mkdocs-ts python API backend for API doc
TG-2380 : Pipeline TS => expose 'dev-server' step
TG-2436 : ♻️ [doc-app] Use `mkdocs-ts` & clean documentation
TG-2435 : 📝 Use sphinx idiom for cross-links
TG-2414 : ♻️ [pipeline TS] Stop using deprecated exported names
TG-2415 : ⬆️ upgrade `deepdiff` to `7.0.1,<8.0.0`
TG-2439 : 📌 `aiohttp<3.10.0`
TG-2438 : 🔥 [yw-utils] Remove unused `aiohttp.TCPConnector`
TG-2452 : Py-youwol v0.1.12
-->

## [0.1.11] − 2024-06-20

### Changed

- **Pipelines**:
  - Enhance reliability of dependencies synchronisation in typescript pipeline. <!-- TG-2366, TG-2368 -->
- **CDN Packaging**:
  - Enhanced the CDN packaging process to support selective Brotli compression and explicit content type
    definitions,  
    allowing for more flexible packaging and optimized download performance. <!-- TG-2353 -->

### Security

- **Dependencies vulnerabilities**:
  - [GHSA-34jh-p97f-mpxf] Upgrade `urllib3` to 2.2.2 <!-- TG-2386 -->
  - [CVE-2024-37890] Upgrade npm package `ws` on documentation app. <!-- TG-2388 -->

## [0.1.10] − 2024-05-27

### Added

- **Documentation**:
  - youwol's API documentation is now generated at build time and served statically. <!-- TG-2235 -->
- **Pipelines**:
  - typescript pipeline provides additional flexibility to customize auto-generated
    `package.json`. <!-- TG-539, TG-1260 -->
- **Registration**:
  - record User-Agent upon account creation & registration <!-- TG-2343 -->

### Fixed

- Use correct separator for `PYTHONPATH` on Windows. <!-- TG-2302 -->
- Addressed issue preventing the projects loader component to properly notify updates regarding projects loading
  failures. <!-- TG-2267 -->
- Resolved an issue related to context propagation within the middleware stack, which previously resulted
  in incorrect parenting of logs. <!-- TG-2331 -->
- Resolved an issue related to inconsistent ordering of keys in auto-generated files of TypeScript
  pipeline. <!-- TG-2336 -->
- Resolved intermittent failures in retrieving Pyodide resources. <!-- TG-2351 -->
- Resolved failures in retrieving Pyodide source-maps. <!-- TG-2359 -->

### Security

- **Dependencies vulnerabilities**:
  - [GHSA-7gpw-8wmc-pm8g] Upgrade `aiohttp` to 3.9.5 <!-- TG-2320 -->
  - [GHSA-g7vv-2v7x-gj9p] Upgrade `tqdm` to 4.66.4 <!-- TG-2333 -->
  - [GHSA-9wx4-h78v-vm56] Upgrade `requests` to 2.32.1 <!-- TG-2337 -->

<!-- Not worthy of inclusion
TG-2121
TG-2327 : ✅ improve IT configuration for performance optimization
TG-2315 : 🚨 Enable pylint rule `raise-missing-from`
TG-2318 : 🚨 Enable pylint rule `use-implicit-booleaness-not-comparison-to-zero`
TG-2319 : 🚨 Enable pylint rule `use-implicit-booleaness-not-comparison-to-string`
TG-2344
TG-2356
TG-2347
TG-2392 : Py-youwol v0.1.11
-->

## [0.1.9] − 2024-04-16

### Added

- **App**:
  - Implemented a browser cache emulation feature to enhance performance for `GET` requests originating from browsers,
    while mitigating the adverse effects associated with native browser cache systems. <!-- TG-2220 -->
- **Backend components**:
  - automatic local installation of missing backends when requesting `backends/$NAME/$SEMVER/**`. <!-- TG-2195 -->
  - explicit local installation on `admin/system/backends/install` using CDN's loading graph
    response. <!-- TG-2205 -->
- **Pyodide components**:
  - intercept Pyodide resources requests to store them within the local CDN database. <!-- TG-2238 -->
- **Pipelines**:
  - configured by default to publish in connected remote and public NPM (if applicable). <!-- TG-2254 -->

### Changed

- **Breaking:** Refactor the `ProjectsFinder` API and its associated implementation to improve performance and
  flexibility. <!-- TG-2228 -->
- Sanitize `EnvironmentStatusResponse` API from `admin/environment/status` endpoint. <!-- TG-2183 -->
- Package Version is now dynamic and stored in attribute `youwol.__version__` <!-- TG-2184 -->
- A link to the `co-lab` portal is now proposed in the terminal at startup. <!-- TG-2233 -->
- Upgrade `GET:/co-lab` target from `@youwol/co-lab#^0.2.0` to `@youwol/co-lab#^0.3.0`. <!-- TG-2231 -->

### Fixed

- Prevent digest infinite recursion and handle more types <!-- TG-2166 -->
- Fix wrong evaluation order of JWT providers in `AuthMiddleware`. <!-- TG-2194 -->
- Discriminates `FailurePipelineNotFound` from `FailureImportException`. <!-- TG-2196 -->
- In pipeline operations involving the local CDN publishing with the packagedFolders option, files located not only
  within the designated packaged folders but also within their subdirectories are now considered. <!-- TG-1683 -->
- `GET:` `/`, `/doc`, `/co-lab`, `/webpm-client.*`: fix issue with browser caching preventing redirects to dynamically
  determined versions. Also, query parameters are now properly forwarded to the redirected URL. <!-- TG-2224 -->
  <!-- TG-2232 -->
- Addressed an issue where version resolution was inaccurately handled under specific scenarios within the
  `cdn-backend` service. <!-- TG-2244 -->
- Addressed an issue related to symbolic links resolution concerning ProjectsFinder when auto-discovery is enabled.
  <!-- TG-2270 -->
- Fix implementation error in the javascript client of backend component regarding the `stream` function.
  <!-- TG-2297 -->

### Security

- **Dependencies vulnerabilities**:
  - On `doc/front-app`: fix [GHSA-cxjh-pqwp-8mfp] <!-- TG-2225 -->
  - [CVE-2024-21503] upgrade `black` to 24.3.0 <!-- TG-2234 -->
  - [GHSA-44wm-f244-xhp3] upgrade `pillow` to 10.3.0 <!-- TG-2271 -->
  - [GHSA-jjg7-2v4v-x38h] upgrade `idna` to 3.7 <!-- TG-2300 -->

### Removed

- The `dev. portal` link proposed in the terminal at startup has been removed . <!-- TG-2233 -->

<!-- Not worthy of inclusion
TG-2286 : 🐛 [app] Allow missing token on `/co-lab`
TG-2284 : 🐛 [app.backends] => `client.stream` do not miss data
TG-2285 : ✨ [utils.Context] => expose `attributes` when creating logs
TG-2272 : 🥅 [pipelines.py_backend] => robustify `generate_template`
TG-2273 : 🐛 [app] `BrowserCacheStore`: don't serve modified files
TG-2269 : 🐛 [app.env.backends] `psutil.net_connections()` => Access denied
TG-2265 : 🐛 [pipeline.py_backend] fix self-contained venvs.
TG-2264 : 🐛 [pipeline.py_backend] fix wrong path from `generate_template`
TG-2263 : 🐛 [app.projects] fix duplicate issue in projects list response
TG-2262 : 🐛 [app] fix backends install can be executed twice
TG-2260 : 🐛 [app] missing update signals from web sockets
TG-2261 : 🐛 [app] missing actual method call in `file_path.exists`
TG-2255 : 🐛 [pipeline.py_backend] => fix missing WS status update
TG-2252 : 🐛 [app] set `no-cache` for downloaded components.
TG-2251 : ♻️ [app] : simplify AssetDownloadThread
TG-2230 : ⚰️ [app.env] => remove `py_youwol_tour` configs
TG-2091 : 🔥 [app.env] => remove deprecated re-export
TG-1218 : 🥅 [backends.cdn] => robustify semver resolution.
TG-2201 : 🙈 [app.env] => default_ignored_paths includes .venv
TG-1507
TG-2210
TG-2205 : ✨ [utils.context] => init `attributes`, `labels` from request.
TG-2187 : 🐛 [routers.local_cdn] => add missing `emit_local_cdn_status`
TG-2213
TG-2226
TG-2246
-->

## [0.1.8] − 2024-03-07

### Added

- **Backend components**:
  - Automated backend installation and initialization upon endpoint request,
    if available in local components. <!-- TG-2085 -->
  - Provide notifications using web-socket regarding installation. <!-- TG-2094 -->
  - Provide endpoints to `terminate` & `uninstall` backends. <!-- TG-2100 -->-
- **Pipeline python backend**:
  - Provide POC version. <!-- TG-2051, TG-2074 -->
  - Add a `Swagger` link to the published component to open the service's 'Swagger UI'. <!-- TG-2098 -->
- **Documentation**:
  - Cross-links w/ youwol's symbols in docstrings more tolerant. <!-- TG 2128 -->
  - Add `admin/system/documentation-check` end point. <!-- TG 2129 -->
  - sync. documentation version with `youwol` version. <!-- TG 2131 -->
  - serve documentation from `/doc`. <!-- TG 2130 -->
  - module's symbols grouped by file. <!-- TG 2143, TG-2146 -->
  - improved code snippets display. <!-- TG-2147 -->
- **Experimental**
  - Configuration dependant browser caching (disabled by default) <!-- TG-2126 -->

### Changed

- **Pipeline Typescript**:
  - upgrade shared configuration `^1.2.1` for latest dependencies:
    - ESlint `^8.56.0` <!-- TG-1997 -->
    - Prettier `^3.2.5` <!-- TG-2070 -->
  - remove pinning of `@types/node`
    after [chokidar bug correction](https://github.com/paulmillr/chokidar/issues/1299) <!-- TG-1983 -->
- Component's type is either `js/wasm` or `backend`. <!-- TG-2080 -->

### Fixed

- Forward request's cookies when using `redirect_request`. <!-- TG-2072 -->
- Ensure python scripts execution has correct environment variable `PYTHONPATH` <!-- TG-2136 -->
- Fix documentation versioning for `.dev` release candidates. <!-- TG 2151 -->
- **Pipeline python backend**:

  - include javascript views within youwol package. <!-- TG-2185 -->
  - `package` step: add required `build` module in python environment. <!-- TG-2186 -->

- Sync. typescript pipeline's `template.py` generator with youwol API updates. <!-- TG-2167 -->
- python backend pipeline: ensure python scripts execution has correct environment variable
  `PYTHONPATH` <!-- TG-2168 -->
- Emit 'components update' signal when publishing a project in local database. <!-- TG-2175 -->
- Prevent digest infinite recursion and handle more types <!-- TG-2166 -->

### Security

- **Dependencies vulnerabilities**:
  - [GHSA-2jv5-9r88-3w3p] upgrade `python-multipart`. to 0.0.9 <!-- TG-2073 -->
  - [CVE-2024-26130] upgrade `cryptography`. to 42.0.4 <!-- TG-2134 -->

### Removed

- Drop support for Python 3.9 <!-- TG-2035, TG-2003 -->

<!-- Not worthy of inclusion
TG-2046
TG-1968
TG-2044
TG-2034
TG-2031
TG-2032
TG-2090
TG-2097
TG-2099
TG-1998
TG-2083
TG-2093
TG-2132
TG-2139
TG-2135
TG-2138
TG-2125
TG-2148
TG-2169
-->

## [0.1.7.post] − 2024-02-09

### Fixed

- **Backends**
  - Error while retrieving token from `Redis` cache if empty <!-- TG-2064 -->

## [0.1.7] − 2024-02-08

### Added

- New Py-youwol documentation application **@youwol/py-youwol-doc
  ** <!-- TG-1923, TG-1924, TG-1925, TG-1951, TG-1952, TG-1961 -->

### Changed

- Improve authentication for HTTP clients <!-- TG-1874 -->
- Improve error management during projects load <!-- TG-1878 -->
- **Pipeline Typescript**:
  - improve step custom views API <!-- TG-1862 -->
  - use caret range for shared configuration dependencies <!-- TG-1912 -->
  - upgrade shared configuration `^1.2.0` for latest dependencies: <!-- TG-1954, TG-1980 -->
    - Typescript `^5.3.3`
    - Jest `^29.5.11`
    - ESlint `8.56.0`
    - Prettier `^3.2.4`
- **Docker images**:
  - use Python 3.12 <!-- TG-1848, TG-1850 -->
  - run as non-privileged user <!-- TG-1957 -->

### Fixed

- Reduce verbosity in terminal when creating project <!-- TG-1735 -->
- **Pipeline Typescript**:
  - allow modifying dependency defined by pipeline using `template.py` <!-- TG-1911 -->
  - format `src/test/fake.ts` <!-- TG-1706 -->
  - pin `@types/node` to `18.19.9`
    for applications until [chokidar issue #1299](https://github.com/paulmillr/chokidar/issues/1299) is
    resolved <!-- TG-1983 -->

### Security

- **Dependencies vulnerabilities**:
  - [CVE-2023-26159] upgrade `follow-redirects` to 1.15.5 <!-- TG-1906 -->
  - [CVE-2024-23334] upgrade `aiohttp` to 3.9.2 <!-- TG-1984 -->
  - [CVE-2024-23829] upgrade `aiohttp` to 3.9.2 <!-- TG-1984 -->
  - [CVE-2023-50782] upgrade `cryptography` to 42.0.2 <!-- TG-2049 -->
  - [CVE-2024-24762] upgrade `fastapi` to 0.109.2, `starlette` to 0.36.3 <!-- TG-2047, TG-2048 -->

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
