import { Routers } from '@youwol/local-youwol-client'
import { Router } from '@youwol/mkdocs-ts'
import { Configuration } from './configurations'
import { VirtualDOM, ChildrenLike } from '@youwol/rx-vdom'
import { PyAttributeView } from './attribute.view'
import { PyDocstringView } from './docstring.view'
import { PyCodeView } from './code.view'
import { HeaderView } from './header.view'
import { PyFunctionView } from './function.view'
import { LinkedTypeView, PyTypeView } from './type.view'
import { separatorView } from './utils'

export class PyClassView implements VirtualDOM<'div'> {
    public readonly fromModule: Routers.System.DocModuleResponse
    public readonly classDoc: Routers.System.DocClassResponse
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly class = 'doc-class doc-item'
    public readonly children: ChildrenLike
    constructor(params: {
        fromModule: Routers.System.DocModuleResponse
        classDoc: Routers.System.DocClassResponse
        router: Router
        configuration: Configuration
    }) {
        Object.assign(this, params)

        this.children = [
            new HeaderView({
                tag: 'h3',
                withClass: 'doc-class-name',
                doc: this.classDoc,
                originPath: this.fromModule.path,
                withChildren: [
                    {
                        tag: 'div',
                        innerText: '(',
                    },
                    ...this.classDoc.bases.map((typeDoc) => {
                        return new PyTypeView({
                            typeDoc,
                            router: this.router,
                            configuration: this.configuration,
                            parent: this.classDoc,
                        })
                    }),
                    {
                        tag: 'div',
                        innerText: ')',
                    },
                ],
            }),
            separatorView,
            new InheritedByView({
                inheritedBy: this.classDoc.inheritedBy,
                router: this.router,
                configuration: this.configuration,
            }),
            new PyCodeView({
                codeDoc: this.classDoc.code,
                router: this.router,
                configuration: this.configuration,
            }),
            { tag: 'div', class: 'mt-3' },
            new PyDocstringView({
                docstring: this.classDoc.docstring,
                router: this.router,
                configuration: this.configuration,
            }),
            ...this.classDoc.attributes.map((attr) => {
                return {
                    tag: 'div' as const,
                    class: 'my-3',
                    children: [
                        new PyAttributeView({
                            attDoc: attr,
                            router: this.router,
                            configuration: this.configuration,
                            parent: this.classDoc,
                            fromModule: this.fromModule,
                            type: 'attribute',
                        }),
                    ],
                }
            }),
            ...this.classDoc.methods.map((method) => {
                return {
                    tag: 'div' as const,
                    class: 'my-3',
                    children: [
                        new PyFunctionView({
                            functionDoc: method,
                            router: this.router,
                            configuration: this.configuration,
                            fromModule: this.fromModule,
                            type: 'method',
                        }),
                    ],
                }
            }),
        ]
    }
}

export class InheritedByView implements VirtualDOM<'div'> {
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly inheritedBy: Routers.System.DocTypeResponse[]
    public readonly tag = 'div'
    public readonly class = 'my-2 p-2'
    public readonly children: ChildrenLike
    constructor(params: {
        inheritedBy: Routers.System.DocTypeResponse[]
        router: Router
        configuration: Configuration
    }) {
        Object.assign(this, params)

        if (this.inheritedBy.length == 0) {
            return
        }

        this.children = [
            {
                tag: 'div',
                class: 'd-flex align-items-center font-weight-bolder',
                children: [
                    {
                        tag: 'div',
                        class: 'fas fa-sitemap pr-2',
                    },
                    {
                        tag: 'div',
                        class: 'pr-2',
                        innerText: 'Inherited by:',
                    },
                ],
            },
            ...params.inheritedBy.map((c) => {
                return {
                    tag: 'div' as const,
                    class: 'px-2',
                    children: [
                        new LinkedTypeView({
                            name: c.name,
                            path: c.path,
                            withChildren: [],
                            configuration: this.configuration,
                            router: this.router,
                        }),
                    ],
                }
            }),
        ]
    }
}
