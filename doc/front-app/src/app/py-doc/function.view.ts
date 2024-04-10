import { Routers } from '@youwol/local-youwol-client'
import { Router } from '@youwol/mkdocs-ts'
import { Configuration } from './configurations'
import { VirtualDOM, ChildrenLike, AnyVirtualDOM } from '@youwol/rx-vdom'
import { PyDocstringView } from './docstring.view'
import { PyCodeView } from './code.view'
import { PyParameterView } from './parameter.view'
import { PyTypeView } from './type.view'
import { HeaderView } from './header.view'
import { separatorView } from './utils'

export class PyFunctionView implements VirtualDOM<'div'> {
    public readonly fromModule: Routers.System.DocModuleResponse
    public readonly functionDoc: Routers.System.DocFunctionResponse
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly class: string
    public readonly children: ChildrenLike

    constructor(params: {
        fromModule: Routers.System.DocModuleResponse
        functionDoc: Routers.System.DocFunctionResponse
        router: Router
        configuration: Configuration
        type: 'function' | 'method'
    }) {
        Object.assign(this, params)
        this.class =
            params.type == 'function'
                ? 'doc-function doc-item'
                : 'doc-method doc-item'
        this.children = [
            new HeaderView({
                tag: params.type == 'function' ? 'h3' : 'h4',
                withClass:
                    params.type == 'function'
                        ? 'doc-function-name'
                        : 'doc-method-name',
                doc: this.functionDoc,
                originPath: this.fromModule.path,
            }),
            new DecoratorsView({
                decorators: this.functionDoc.decorators,
                configuration: this.configuration,
            }),
            separatorView,
            new PyCodeView({
                codeDoc: this.functionDoc.code,
                router: this.router,
                configuration: this.configuration,
            }),
            new PyDocstringView({
                docstring: this.functionDoc.docstring,
                router: this.router,
                configuration: this.configuration,
            }),
            {
                tag: 'span',
                style: {
                    fontWeight: 'bolder',
                },
                class: 'doc doc-object-name',
                innerText: 'parameters',
            },
            ...this.functionDoc.parameters.map((paramDoc) => {
                return {
                    tag: 'div' as const,
                    class: 'my-3 pl-3',
                    children: [
                        new PyParameterView({
                            paramDoc: paramDoc,
                            router: this.router,
                            configuration: this.configuration,
                            parent: this.functionDoc,
                        }),
                    ],
                }
            }),
            ...this.returnView(),
        ]
    }

    returnView(): AnyVirtualDOM[] {
        return this.functionDoc.returns
            ? [
                  {
                      tag: 'span',
                      style: {
                          fontWeight: 'bolder',
                      },
                      class: 'doc doc-object-name doc-return-name',
                      innerText: 'return',
                  },
                  {
                      tag: 'div' as const,
                      class: 'my-3 pl-3',
                      children: [
                          this.functionDoc?.returns?.type
                              ? new PyTypeView({
                                    typeDoc: this.functionDoc.returns.type,
                                    router: this.router,
                                    configuration: this.configuration,
                                    parent: this.functionDoc,
                                })
                              : undefined,
                          new PyDocstringView({
                              docstring: this.functionDoc.returns?.docstring,
                              router: this.router,
                              configuration: this.configuration,
                          }),
                      ],
                  },
              ]
            : []
    }
}

export class DecoratorsView implements VirtualDOM<'div'> {
    public readonly tag = 'div'
    public readonly class = 'my-2'
    public readonly children: ChildrenLike

    constructor(params: {
        decorators: { path: string }[]
        configuration: Configuration
    }) {
        this.children = params.decorators.map(({ path }) => {
            const customView = params.configuration.decoratorView({ path })
            return (
                customView || {
                    tag: 'pre',
                    innerText: path,
                }
            )
        })
    }
}
