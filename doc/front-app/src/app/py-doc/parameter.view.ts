import { ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { Router } from '@youwol/mkdocs-ts'
import { Configuration } from './index'
import { Routers } from '@youwol/local-youwol-client'
import { PyTypeView } from './type.view'
import { PyDocstringView } from './docstring.view'

export class PyParameterView implements VirtualDOM<'div'> {
    public readonly paramDoc: Routers.System.DocParameterResponse

    public readonly parent: unknown
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly children: ChildrenLike
    constructor(params: {
        router: Router
        paramDoc: Routers.System.DocParameterResponse
        configuration: Configuration
        parent: unknown
    }) {
        Object.assign(this, params)
        this.children = [
            {
                tag: 'div',
                class: 'd-flex align-items-center doc doc-heading',
                children: [
                    {
                        tag: 'span',
                        style: {
                            fontWeight: 'bolder',
                        },
                        class: 'doc doc-object-name doc-parameter-name',
                        innerText: this.paramDoc.name,
                    },
                    { tag: 'div', class: 'mx-2' },
                    { tag: 'div', innerText: ':' },
                    { tag: 'div', class: 'mx-2' },
                    this.paramDoc.type
                        ? new PyTypeView({
                              typeDoc: this.paramDoc.type,
                              router: this.router,
                              configuration: this.configuration,
                              parent: this.paramDoc,
                          })
                        : { tag: 'div', innerText: 'any' },
                ],
            },

            new PyDocstringView({
                docstring: this.paramDoc.docstring,
                router: this.router,
                configuration: this.configuration,
            }),
        ]
    }
}
