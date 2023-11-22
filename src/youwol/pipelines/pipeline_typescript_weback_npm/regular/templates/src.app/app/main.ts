require('./style.css')
export {}
import * as webpmClient from '@youwol/webpm-client'

import { setup } from '../auto-generated'

await setup.installMainModule({
    cdnClient: webpmClient,
    installParameters: {
        css: [
            'bootstrap#4.4.1~bootstrap.min.css',
            'fontawesome#5.12.1~css/all.min.css',
            '@youwol/fv-widgets#latest~dist/assets/styles/style.youwol.css',
        ],
        displayLoadingScreen: true,
    },
})

await import('./on-load')
