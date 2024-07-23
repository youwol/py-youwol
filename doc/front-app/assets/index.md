# Py-YouWol

<note level='hint' label="">
Py-YouWol is a Python server running on your PC, emulating a cloud server. 
It automatically installs and links executable units—JavaScript ESM modules, backend services, and Pyodide modules—
each time applications are loaded from your web browser.
</note>

The solution is built on three foundational concepts:

- **Online Ecosystem**: This ecosystem integrates a range of assets, including front-end applications/libraries,
  backend services, and data.
  These assets are transparently installed on your PC upon request, typically when accessing a URL.
- **Dynamic linking**: Applications can dynamically install and link components based on semantic versioning,
  ensuring you always get the latest compatible versions of the required components.
  Additionally, dependency resolution considers both the online ecosystem and your local projects.
- **Local Python-Based Server**: Acting as the orchestrator, this server facilitates the access and download of various
  assets from the ecosystem to your PC. It provides services for data management, user sessions, authentication,
  and maintains flexibility to meet diverse developer needs.

Benefits include:

- **Powerful applications**: The ability to install and link components on the fly—including backends—offers great
  opportunities to build complex applications.
- **Security**: Since Py-YouWol runs on your PC, your applications can consume data only available locally.
- **Efficiency**: Once downloaded, assets remain on your PC and are not re-downloaded unless a new version is
  available and requested.
  Additionally, the local server offers multiple mechanisms to enhance efficiency at various levels.
- **Reduced development cycle**: Dynamic dependency resolution that includes local projects leads to a more agile and
  responsive development process.
  Additionally, Py-YouWol provides a dedicated application called co-lab to manage your local projects and environments.

<note level="warning" label="Important">
When developing components for Py-YouWol, there is little to no specific consideration required.
Py-YouWol offers solutions that you can choose to use or not.
</note>

## Getting started

<note level="warning" label="Windows">
Currently, py-youwol is not yet compatible with the Windows OS. We are actively working on adding support.
</note>

We recommend using [pipx](https://github.com/pypa/pipx) to run youwol using the latest compatible version of python ({PYTHON_RECOMMENDED}):

```shell
pipx run youwol=={YW_VERSION}
```

Once started (assuming the default port `2000` is used),
any application available in the ecosystem can be loaded through the URL:

`http://locahost:2000/applications/$APP_NAME/$APP_VERSION`

where:

- `$APP_VERSION` is the name of the application.
- `$APP_VERSION` is the version requests, or a semver query.

More information regarding installation can be found [here](@nav/how-to/install-youwol.md),
command line options to start youwol are explained [here](@nav/how-to/start-youwol.md).

<note level="hint">
Applications that do not require a backend can be accessed online, if the necessary components
are published and accessible, at the following URL:

`https://platform.youwol.com/applications/$APP_NAME/$APP_VERSION`
</note>

## Next Steps

<note level="warning">
The following links assume Py-YouWol running on the port `2000`.
</note>

### Interactive Tutorial

The Py-YouWol server includes a front-end application called [CoLab](http://localhost:2000/co-lab),
which exposes the current environment, downloaded components, your projects, and more.
It features a dedicated section for [documentation](http://localhost:2000/co-lab/doc), providing tutorials that guide
you through the solution's features and usage, particularly for publishing your projects.

### WebPM Client

WebPM is the JavaScript client library that enables dynamic installation and linking of dependencies.
Its [documentation](http://localhost:2000/applications/@youwol/webpm-client-doc/latest) covers topics such as
installing ESM, Pyodide, and backend modules, as well as creating web-worker pools.

### Gallery

Our [gallery](http://localhost:2000/applications/@youwol/gallery/latest) showcases a collection of selected
applications, often presented in the form of notebooks.
These examples illustrate the capabilities of Py-YouWol and what can be achieved with it.

### Notebook

One of our most popular libraries is `@youwol/mkdocs-ts`, which provides tools to create hierarchical documents
like this one.
It also enables the inclusion of notebook-like pages with advanced features thanks to Py-YouWol solutions.
You can find presentations and tutorials
[here](http://localhost:2000/applications/@youwol/mkdocs-ts-doc/0.5.5-wip?nav=/tutorials/notebook).

### API Documentation

The API documentation of Py-YouWol can be found within this document in the [API](@nav/api) section.
