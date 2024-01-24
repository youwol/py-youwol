import { ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { Configuration } from './index'
import { Routers } from '@youwol/local-youwol-client'
import { PyClassView } from './class.view'
import { PyDocstringView } from './docstring.view'
import { PyFunctionView } from './function.view'
import { HeaderView } from './header.view'
import { PyAttributeView } from './attribute.view'
import { Router } from '@youwol/mkdocs-ts'
import { separatorView } from './utils'

export class PyModuleView implements VirtualDOM<'div'> {
    public readonly moduleDoc: Routers.System.DocModuleResponse
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly children: ChildrenLike
    constructor(params: {
        moduleDoc: Routers.System.DocModuleResponse
        router: Router
        configuration: Configuration
    }) {
        Object.assign(this, params)
        this.children = [
            new HeaderView({
                tag: 'h1',
                withClass: 'doc-module-name',
                doc: this.moduleDoc,
                originPath: this.moduleDoc.path,
            }),
            {
                tag: 'div',
                children: [
                    new PyDocstringView({
                        docstring: this.moduleDoc.docstring || '',
                        router: this.router,
                        configuration: this.configuration,
                    }),
                ],
            },
            { tag: 'div', class: 'my-3' },
            separatorView,
            { tag: 'div', class: 'my-5' },
            {
                tag: 'div',
                children: this.moduleDoc.attributes.map(
                    (attDoc) =>
                        new PyAttributeView({
                            fromModule: this.moduleDoc,
                            attDoc,
                            router: this.router,
                            configuration: this.configuration,
                            parent: this.moduleDoc,
                            type: 'global',
                        }),
                ),
            },
            {
                tag: 'div',
                children: this.moduleDoc.functions.map(
                    (functionDoc) =>
                        new PyFunctionView({
                            fromModule: this.moduleDoc,
                            functionDoc,
                            router: this.router,
                            configuration: this.configuration,
                            type: 'function',
                        }),
                ),
            },
            {
                tag: 'div',
                children: this.moduleDoc.classes.map(
                    (classDoc) =>
                        new PyClassView({
                            fromModule: this.moduleDoc,
                            classDoc,
                            router: this.router,
                            configuration: this.configuration,
                        }),
                ),
            },
        ]
    }
}
