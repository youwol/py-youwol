# {{name}}


{{description}}


## Installation, Build & Test 

To install the required dependencies:
```shell
yarn 
```

To build for development:
```shell
yarn build:dev
```

To build for production:
```shell
yarn build:prod
```

To test:
```shell
yarn test
```

To generate code documentation:
```shell
yarn doc
```

## Developing Flux-Packs

> The [Youwol fullstack environment](https://pypi.org/project/youwol/) should be used when developing
> *flux-pack*. It offers an immersive experience of the YouWol ecosystem, and lets
> you work with your favorite stack. Usually you've accessed this file using it anyway.
> All the links in what follows assumed you've started this environment.

### Using your modules in a *flux-app*

If not already done, *build, test & publish* the package from the [dashboard](/ui/dashboard-developer/).

Start by creating a new *flux-app*:
-    short version: follow [this link](/ui/flux-builder/?uri=%7B%22name%22%3A%22new%20flux-project%22%2C%22description%22%3A%22%22%2C%22runnerRendering%22%3A%7B%22layout%22%3A%22%22%2C%22style%22%3A%22%22%7D%2C%22builderRendering%22%3A%7B%22descriptionsBoxes%22%3A%5B%5D%2C%22modulesView%22%3A%5B%5D%2C%22connectionsView%22%3A%5B%5D%7D%2C%22requirements%22%3A%7B%22fluxComponents%22%3A%5B%5D%2C%22fluxPacks%22%3A%5B%5D%2C%22libraries%22%3A%7B%7D%2C%22loadingGraph%22%3A%7B%22graphType%22%3A%22sequential-v1%22%2C%22lock%22%3A%5B%5D%2C%22definition%22%3A%5B%5B%5D%5D%7D%7D%2C%22workflow%22%3A%7B%22modules%22%3A%5B%5D%2C%22connections%22%3A%5B%5D%2C%22plugins%22%3A%5B%5D%2C%22rootLayerTree%22%3A%7B%22layerId%22%3A%22rootLayer%22%2C%22moduleIds%22%3A%5B%5D%2C%22title%22%3A%22rootLayer%22%2C%22children%22%3A%5B%5D%7D%7D%7D), you won't be able to save your changes
-   long version: from the [workspace](/ui/workspace-explorer/), navigate in the explorer into your **private** group,
eventually create a drive and a folder, and with a right click select **new app**. You can now start its construction (click 
on **construct** after having selected it in your workspace).

Once opened, in the top *builder-panel*:
-    right click + 'new module(s)'
-    expand the 'explorer node'
-    navigate to **private** / **default-drive** / ${name of your flux-pack}
-    select 'A simple module' and click 'OK'


### Starting designing your modules

To go beyond the [[ SimpleModule | provided example]], you should have a first pass on the 
[flux-core documentation](/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/core_concepts.html).


### Version management 

In order to conveniently work within YouWol's environment, the following 
approach regarding versioning is recommended:
-   when you start a new version of your package (e.g. from a version *0.1.2*)
you append a *-next* to the version you've started from (e.g. *0.1.2-next*). 
    Among other things, it will ensure that your browser won't cache your source code.
-   when iterating over the same version, just keep the *-next* and publish to the CDN
    whenever you want to try your modules in Flux.
-   when you want to finalize a version: (i) pick the right version number 
    (e.g. *0.1.3*, *0.2.0*, etc ), (ii) go through 'build/test/publish CDN', 
    and (iii) eventually publish your package in a npm repository.

> The CDN is accepting to override previous publish version, this
> is how the *-next* trick is working and allows for a smooth integrated 
> experience. However, when a finalized version of your package is published
> (with no *-next* suffix), it is strongly recommended to not update the
> CDN content of your package anymore for this version.

> If you plan to share your package, you'll need to publish it in a npm repository.
> For public or private needs, the choice of this repository is yours.
> For more advanced permission resolution related to YouWol's group, you'll need to use your 
> YouWol's GitLab environment (not available yet).
