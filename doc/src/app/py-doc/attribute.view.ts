import { ChildrenLike, VirtualDOM, AnyVirtualDOM } from '@youwol/rx-vdom'
import { Router, parseMd } from '@youwol/mkdocs-ts'
import { Configuration } from './index'
import { Routers } from '@youwol/local-youwol-client'
import { PyDocstringView } from './docstring.view'
import { HeaderView } from './header.view'
import { PyTypeView } from './type.view'

export class PyAttributeView implements VirtualDOM<'div'> {
    public readonly attDoc: Routers.System.DocAttributeResponse
    public readonly fromModule: Routers.System.DocModuleResponse

    public readonly parent: unknown
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly class: string
    public readonly children: ChildrenLike
    constructor(params: {
        router: Router
        attDoc: Routers.System.DocAttributeResponse
        configuration: Configuration
        parent: unknown
        fromModule: Routers.System.DocModuleResponse
        type: 'attribute' | 'global'
    }) {
        Object.assign(this, params)
        this.class =
            params.type == 'attribute'
                ? 'doc-attribute doc-item'
                : 'doc-global doc-item'

        const headerChildren: AnyVirtualDOM[] = [
            { tag: 'div', innerText: ':', class: 'mx-4' },
            this.attDoc.type
                ? new PyTypeView({
                      typeDoc: this.attDoc.type,
                      router: this.router,
                      configuration: this.configuration,
                      parent: this.attDoc,
                  })
                : { tag: 'div', innerText: 'any' },
        ]

        this.children = [
            {
                tag: 'div',
                class: 'd-flex align-items-center',
                children: [
                    new HeaderView({
                        tag: params.type === 'attribute' ? 'h3' : 'h2',
                        withClass:
                            params.type === 'attribute'
                                ? 'doc-attribute-name'
                                : 'doc-global-name',
                        doc: this.attDoc,
                        originPath: this.fromModule.path,
                        withChildren: headerChildren,
                    }),
                ],
            },
            {
                tag: 'div',
                children: [
                    parseMd({
                        src:
                            '```python\n' +
                            this.attDoc.code.content +
                            '\n```\n',
                        router: this.router,
                    }),
                ],
            },
            {
                tag: 'div',
                class: 'px-3 py-2',
                children: [
                    new PyDocstringView({
                        docstring: this.attDoc.docstring,
                        router: this.router,
                        configuration: this.configuration,
                    }),
                ],
            },
        ]
    }
}
