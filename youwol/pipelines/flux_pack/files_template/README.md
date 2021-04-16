# {{name}}

<p>
    <a href="https://github.com/kefranabg/readme-md-generator/graphs/commit-activity" target="_blank">
        <img alt="Maintenance" src="https://img.shields.io/badge/Maintained%3F-yes-green.svg" />
    </a>
    <a href="https://github.com/kefranabg/readme-md-generator/blob/master/LICENSE" target="_blank">
        <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" />
    </a>
</p>

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

## Usage 



## Resources

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
> GitLab environment.
