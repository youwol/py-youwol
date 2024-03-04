import { AnyVirtualDOM, ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { Router, parseMd } from '@youwol/mkdocs-ts'
import { Configuration } from './index'
import { Routers } from '@youwol/local-youwol-client'

export class PyDocstringView implements VirtualDOM<'div'> {
    public readonly docstring?:
        | string
        | Routers.System.DocDocstringSectionResponse[]
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly children: ChildrenLike
    constructor(params: {
        docstring?: string | Routers.System.DocDocstringSectionResponse[]
        router: Router
        configuration: Configuration
    }) {
        Object.assign(this, params)

        const redirect = (
            link: HTMLAnchorElement,
            target: string,
            i: number,
        ) => {
            const href = link.href.split(target)[1]
            let path =
                i == 0
                    ? `/references/${href.split('.').join('/')}`
                    : `/references/${href.split('.').slice(0, -i).join('/')}.${
                          href.split('.').slice(-i)[0]
                      }.${href.split('.').slice(-i)[1]}`
            if (i > 2) {
                path += `.${href.split('.').slice(-2)[1]}`
            }
            this.router.navigateTo({ path })
        }

        const navigations = {
            'yw-nav-mod': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-mod:', 0),
            'yw-nav-class': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-class:', 2),
            'yw-nav-func': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-func:', 2),
            'yw-nav-attr': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-attr:', 3),
            'yw-nav-glob': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-glob:', 2),
            'yw-nav-meth': (link: HTMLAnchorElement) =>
                redirect(link, '@yw-nav-meth:', 3),
        }

        let parsed: AnyVirtualDOM[] = []
        if (Array.isArray(this.docstring)) {
            parsed = this.docstring
                .map((d) => {
                    return [
                        d.title
                            ? new SectionHeader({
                                  title: d.title,
                                  withTag: d.tag,
                              })
                            : undefined,
                        parseMd({
                            src: d.text,
                            router: this.router,
                            navigations,
                        }),
                    ]
                })
                .flat()
        }
        if (typeof this.docstring == 'string') {
            parsed = [
                parseMd({
                    src: this.docstring,
                    router: this.router,
                    navigations,
                }),
            ]
        }
        this.children = parsed
    }
}

export class SectionHeader implements VirtualDOM<'div'> {
    public readonly title: string
    public readonly withTag?: string
    public readonly tag = 'div'
    public readonly children: ChildrenLike
    public readonly class =
        'w-100 p-2 my-3 d-flex align-items-center text-dark border-bottom'

    constructor(params: { withTag?: string; title: string }) {
        Object.assign(this, params)
        const factory = {
            warning: 'fas fa-exclamation fv-text-focus',
            example: 'fas fa-code fv-text-success',
            todos: 'fas fa-forward fv-text-success',
        }
        this.children = [
            {
                tag: 'div',
                class: factory[this.withTag] || 'fas fa-info fv-text-success',
            },
            { tag: 'div', class: 'mx-2' },
            {
                tag: 'div',
                innerText: this.title,
            },
        ]
    }
}
