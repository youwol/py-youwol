YouWol, your web-based open laboratory, offers a collaborative environment for developing and sharing browser-based
applications.
It's an innovative hybrid solution, seamlessly blending the flexibility of local customization,
typical of PC environments, with the accessibility of cloud technologies, all operating directly on your PC via your
web browser.

**Because it runs in a browser**:

- Seamless and transparent lazy fetching of everything (backends, frontends, data) when accessing a URL.
- Frontend libraries are executed in an OS-independent environment, taking advantages of a standardized API
  to access diverse peripherals as well as performance-oriented solutions.

**Because it is hosted in your PC**:

- After initial fetched, data are persisted forever, improving performances
- Applications can rely on backends, that gets downloaded and run transparently in your PC
- Applications can use data that only exists in your PC
- Linking an application against libraries or backends accounts for versions that may only exist
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

1.  Thinking of Multi-threading, GPU, WebAssembly, Python, ESM, _etc_
