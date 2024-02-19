# YouWol

YouWol, your web-based open laboratory, offers a collaborative environment for developing and sharing browser-based
applications.
It's an innovative hybrid solution, seamlessly blending the flexibility of local customization,
typical of PC environments, with the accessibility of cloud technologies, all operating directly on your PC via your
web browser.

<!--
**Because it runs in a browser**:

*  Seamless and transparent lazy fetching of everything (backends, frontends, data) when accessing a URL.
*  Frontend libraries are executed in an OS-independent environment, taking advantages of a standardized API
to access diverse peripherals as well as performance-oriented solutions.

**Because it is hosted in your PC**:

*  After initial fetched, data are persisted forever, improving performances
*  Applications can rely on backends, that gets downloaded and run transparently in your PC
*  Applications can use data that only exists in your PC
*  Linking an application against libraries or backends accounts for versions that may only exist
in your computer (before publishing them).

It is a novel type of hybrid local/cloud solution that aims to provide an environment highly customizable
(just like PC), as well as widely accessible (just like cloud platform).

Here's a practical example for clarification. Suppose a user is using an application called `foo` that relies on a component
named `bar` (be it frontend or backend). When this user release a new compatible version of `bar` locally on his computer,
`foo` will automatically pick the change. Subsequently, when he published the updated version of `bar` online,
everyone else will receive the update the next time they use `foo` on their computer. In the same line, this mechanism
also applies for data. Constructed using contemporary and standard web technologies (1), it positions YouWol as an ideal
collaborative space for research and development, fostering innovation.
{ .annotate }
1.  Thinking of Multi-threading, GPU, WebAssembly, Python, ESM, *etc*

-->

The solution is built on three foundational concepts:

- **Online Ecosystem**: This ecosystem brings together a range of assets, including front-end applications/libraries,
  backend services, and data. They get installed in your PC transparently upon request (usually when accessing a URL).
- **Dynamic linking**: While regular web application are statically linked to front-end libraries or backend services,
  in youwol dependencies are linked dynamically. _E.g._ an application always get the latest compatible version of a dependency,
  including a version that may only exist in your computer (e.g. before publishing it).
- **Local Python-Based Server**: Serving as the orchestrator, this server facilitates access and potential downloads
  of various assets from the ecosystem to the user's PC.
  It provides services for data management, user sessions, authentications, and maintains flexibility to meet diverse developer needs.

<!--
The essence of YouWol lies in fostering collaboration:

*  **Automatic Data Sharing**: In YouWol, data behaves like files organized in a tree structure resembling a file system.
Upon publishing, data automatically downloads when requested by any YouWol user (subject to permissions).
*  **Automatic Code Sharing**: When new versions of libraries/backends get published, either in the ecosystem or in your
PC as work in progress, they get automatically caught up by application and linked dynamically.
*  **Collaborative Operating System**: Building on the previous points, YouWol facilitates the emulation of
an operating system within web browsers. Going beyond conventional OS, it can be accessed from any browser, enables
seamless sharing of environments & profiles, and more.
-->

## Getting started

We recommend using [pipx](https://github.com/pypa/pipx) to run youwol using the latest compatible version of python ({PYTHON_RECOMMENDED}):

```shell
pipx run youwol=={YW_VERSION}
```

Once started (assuming the default port `2000`is used),
any application available in the ecosystem can be loaded through the URL:

`locahost:2000/applications/$APP_NAME/$APP_VERSION`

where:

- `$APP_VERSION` is the name of the application.
- `$APP_VERSION` is the version requests, or a semver query.

More information regarding installation can be found [here](@nav/how-to/install-youwol.md),
command line options to start youwol are explained [here](@nav/how-to/start-youwol.md).

## Documentation organization

From now on, the documentation is assuming that youwol is running on your computer from the port `2000`.

The section **Gallery** provides some links of selected applications, they serve as illustration of the kind
of applications that can be developed within YouWol.

For developers who want to contribute to the ecosystem, the **Tutorials** section is a great place
to start. In a couple of minutes you will be able to publish and share applications, libraries as well as backends.

Advanced topics are presented in the sections **How-To Guides**, while the **References** section describes
the YouWol API.
