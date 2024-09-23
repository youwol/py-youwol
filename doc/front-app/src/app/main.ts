require('./style.css')
export {}
import * as webpmClient from '@youwol/webpm-client'

import { setup } from '../auto-generated'

await setup.installMainModule({
    cdnClient: webpmClient,
    installParameters: {
        css: [
            'bootstrap#5.3.3~bootstrap.min.css',
            'fontawesome#5.12.1~css/all.min.css',
            '@youwol/fv-widgets#latest~dist/assets/styles/style.youwol.css',
            'highlight.js#11.2.0~styles/default.css',
            `@youwol/mkdocs-ts#${setup.runTimeDependencies.externals['@youwol/mkdocs-ts']}~assets/mkdocs-light.css`,
            `@youwol/mkdocs-ts#${setup.runTimeDependencies.externals['@youwol/mkdocs-ts']}~assets/notebook.css`,
        ],
        displayLoadingScreen: true,
    },
})

await import('./on-load')
