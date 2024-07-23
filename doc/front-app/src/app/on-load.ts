import { render } from '@youwol/rx-vdom'
import { navigation } from './navigation'
import { setup } from '../auto-generated'
import { Router, Views } from '@youwol/mkdocs-ts'

export const router = new Router({
    navigation,
})

document.getElementById('content').appendChild(
    render(
        new Views.DefaultLayoutView({
            router,
            name: 'Py-YouWol',
            topBanner: (params) =>
                new Views.TopBannerClassicView({
                    ...params,
                    logo: {
                        tag: 'img',
                        src: '../assets/logo_YouWol.svg',
                        style: {
                            height: '30px',
                        },
                    },
                    badge: new Views.SourcesLink({
                        href: 'https://github.com/youwol/py-youwol/',
                        version: setup.version,
                        name: 'py-youwol',
                    }),
                }),
        }),
    ),
)
