require('./style.css')
export {}
const cdn = window['@youwol/cdn-client']
import { setup } from '../auto-generated'

await cdn.install({
    modules: Object.entries(setup.runTimeDependencies.load).map(
        ([k, v]) => `${k}#${v}`,
    ),
    css: [
        'bootstrap#4.4.1~bootstrap.min.css',
        'fontawesome#5.12.1~css/all.min.css',
        '@youwol/fv-widgets#latest~dist/assets/styles/style.youwol.css',
    ],
    displayLoadingScreen: true,
})

await import('./on-load')
