import { ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { BehaviorSubject } from 'rxjs'
import { parseMd, Router } from '@youwol/mkdocs-ts'
import { Routers } from '@youwol/local-youwol-client'
import { Configuration } from './index'

class PyCodeHeaderView implements VirtualDOM<'div'> {
    public readonly codeDoc: Routers.System.DocCodeResponse
    public readonly configuration: Configuration

    public readonly tag = 'div'
    public readonly class = 'd-flex align-items-center border rounded p-1 w-100'
    public readonly style = {
        fontSize: '0.8rem',
        backgroundColor: 'rgba(0,0,0,0.1)',
    }
    public readonly children: ChildrenLike
    public readonly expanded$: BehaviorSubject<boolean>

    constructor(params: {
        codeDoc: Routers.System.DocCodeResponse
        expanded$: BehaviorSubject<boolean>
        configuration: Configuration
    }) {
        Object.assign(this, params)
        const path = `youwol/${this.codeDoc.filePath.split('/youwol/')[1]}`
        this.children = [
            {
                tag: 'i',
                class: 'fas fa-code',
            },
            {
                tag: 'div',
                class: 'mx-2',
            },
            {
                tag: 'div',
                innerText: 'Source code in ',
            },
            {
                tag: 'a',
                class: 'my-0 mx-2',
                innerText: path,
                target: '_blank',
                href: this.configuration.codeUrl(path, this.codeDoc.startLine),
            },
            {
                tag: 'div',
                class: 'flex-grow-1',
            },
            {
                tag: 'div',
                class: {
                    source$: this.expanded$,
                    vdomMap: (expanded: boolean) =>
                        expanded ? 'fa-chevron-down' : 'fa-chevron-right',
                    wrapper: (d) => `fas fv-pointer ${d}`,
                },
                onclick: () => this.expanded$.next(!this.expanded$.value),
            },
        ]
    }
}
export class PyCodeView implements VirtualDOM<'div'> {
    public readonly router: Router
    public readonly codeDoc: Routers.System.DocCodeResponse
    public readonly configuration: Configuration

    public readonly tag = 'div'
    public readonly class = 'fv-border-primary rounded'
    public readonly style = {
        fontSize: '0.9rem',
    }
    public readonly children: ChildrenLike
    public readonly expanded$ = new BehaviorSubject(false)
    constructor(params: {
        codeDoc: Routers.System.DocCodeResponse
        router: Router
        configuration: Configuration
    }) {
        Object.assign(this, params)
        this.children = [
            new PyCodeHeaderView({
                codeDoc: this.codeDoc,
                expanded$: this.expanded$,
                configuration: this.configuration,
            }),
            {
                source$: this.expanded$,
                vdomMap: (expanded: boolean) => {
                    if (!expanded) {
                        return { tag: 'div' }
                    }
                    return {
                        tag: 'div',
                        class: 'ml-1 mr-1 mt-1',
                        children: [
                            parseMd({
                                src: `<code-snippet language="python">${this.codeDoc.content}</code-snippet>`,
                                router: this.router,
                            }),
                        ],
                    }
                },
            },
        ]
    }
}
