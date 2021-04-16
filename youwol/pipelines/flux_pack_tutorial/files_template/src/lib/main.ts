import { Environment, FluxPack } from '@youwol/flux-lib-core'
import { NAME, VERSION, DESCRIPTION, URL_CDN } from '../auto-generated'

/**
 This variable is declaring the flux-pack, we usually include this variable in a file 'main.ts'

 Most of the times it is constructed using the the [[auto-generated | auto-generated]] attributes from package.json:

 ```typescript
 import { Environment, FluxPack } from '@youwol/flux-lib-core'
 import { NAME, VERSION, DESCRIPTION, URL_CDN, ASSET_ID } from '../auto-generated'

 export let pack = new FluxPack({

     name: NAME,
     version: VERSION,
     assetId: ASSET_ID,
     description: DESCRIPTION,
     urlCDN: URL_CDN,
     install: ( environment: Environment ) => {
     // see documentation
     }
})
 ```

    In a typical scenario, you will only be interested by the **install** function.

 ### name

 The name of the pack, usually the package's name

 ### version

 The version of the pack, usually the package's version

 ### assetId

 The is the assetId that identifies this flux-pack resource in the YouWol asset store.

 ### description

 The description of the pack, usually the package's description

 ### urlCDN

 The base path of the url corresponding to the root of the package, usually using the *URL_CDN* auto-generated
 variable.

  ### install (optional)

 The function install some required resources after the package is loaded from the CDN.

 It is for instance possible to load javascript add-ons of the package dynamically using
 **environment.fetchJavascriptAddOn**.
 Another common use case is to load css resources using **environment.fetchStyleSheets**
 Both functions are returning an Observable and takes as argument an array of url pointers.
 Url pointers are in the format: {package-name}#{version}~{path-from-cdn-root}

 The *install* function must return a promise or an observable.
 To combine multiple observables or promises you
 can look at
 [rxjs.forkJoin](https://www.learnrxjs.io/learn-rxjs/operators/combination/forkjoin) or
 [Promise.All](https://developer.mozilla.org/fr/docs/Web/JavaScript/Reference/Global_Objects/Promise/all)
 respectively.
 */
export let pack = new FluxPack({

    id: NAME,
    version: VERSION,    
    description: DESCRIPTION,
    urlCDN: URL_CDN,
    install: ( environment: Environment ) => {
    }
})

