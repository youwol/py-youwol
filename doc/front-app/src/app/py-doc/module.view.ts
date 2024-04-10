import { ChildrenLike, VirtualDOM, AnyVirtualDOM } from '@youwol/rx-vdom'
import { Configuration } from './configurations'
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
        console.log('View', params.moduleDoc)
        const getFile = ({ path }) => {
            return path.split('.').slice(-2)[0]
        }
        const files = [
            ...new Set(
                [
                    ...this.moduleDoc.attributes,
                    ...this.moduleDoc.functions,
                    ...this.moduleDoc.classes,
                ].map(getFile),
            ),
        ].sort((a: string, b: string) => a.localeCompare(b))

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
            ...[...files].map((file): AnyVirtualDOM => {
                const attributes = this.moduleDoc.attributes.filter(
                    (a) => getFile(a) == file,
                )
                const classes = this.moduleDoc.classes.filter(
                    (a) => getFile(a) == file,
                )
                const functions = this.moduleDoc.functions.filter(
                    (a) => getFile(a) == file,
                )
                const fileDoc = this.moduleDoc.files.find((f) => {
                    return f.path.split('.').slice(-1)[0] == file
                })
                return {
                    tag: 'div' as const,
                    children: [
                        { tag: 'div', class: 'my-5' },
                        new HeaderView({
                            tag: 'h2',
                            withClass: 'doc-file-name fas fa-file',
                            text: `  ${file}.py`,
                            doc: this.moduleDoc,
                            originPath: this.moduleDoc.path,
                        }),
                        new PyDocstringView({
                            docstring: fileDoc.docstring || '',
                            router: this.router,
                            configuration: this.configuration,
                        }),
                        {
                            tag: 'div',
                            children: attributes.map(
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
                            children: functions.map(
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
                            children: classes.map(
                                (classDoc) =>
                                    new PyClassView({
                                        fromModule: this.moduleDoc,
                                        classDoc,
                                        router: this.router,
                                        configuration: this.configuration,
                                    }),
                            ),
                        },
                    ],
                }
            }),
        ]
    }
}
