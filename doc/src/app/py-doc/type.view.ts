import { AnyVirtualDOM, ChildrenLike, VirtualDOM } from '@youwol/rx-vdom'
import { Routers } from '@youwol/local-youwol-client'
import { Router } from '@youwol/mkdocs-ts'
import { Configuration } from './index'

export class PyTypeView implements VirtualDOM<'div'> {
    public readonly typeDoc: Routers.System.DocTypeResponse
    public readonly parent: unknown
    public readonly router: Router
    public readonly configuration: Configuration

    public readonly tag = 'div'
    public readonly class = 'd-flex align-items-center mx-1 '
    public readonly children: AnyVirtualDOM[]

    constructor(params: {
        typeDoc: Routers.System.DocTypeResponse
        router: Router
        configuration: Configuration
        parent: unknown
    }) {
        Object.assign(this, params)

        const children =
            this.typeDoc?.generics?.length > 0
                ? [
                      {
                          tag: 'div' as const,
                          innerText: '[',
                      },
                      ...this.genericsView(),
                      {
                          tag: 'div' as const,
                          innerText: ']',
                      },
                  ]
                : []
        if (!this.typeDoc) {
            this.children = [this.defaultView(children)]
            return
        }
        this.children = [
            new LinkedTypeView({
                name: this.typeDoc.name,
                path: this.typeDoc.path,
                configuration: this.configuration,
                router: this.router,
                withChildren: children,
            }),
        ]
    }

    private genericsView() {
        return this.typeDoc.generics
            .map((t, i) => [
                ...new PyTypeView({
                    typeDoc: t,
                    router: this.router,
                    configuration: this.configuration,
                    parent: t,
                }).children,
                i < this.typeDoc.generics.length - 1
                    ? {
                          tag: 'div' as const,
                          innerText: ',',
                      }
                    : { tag: 'div' as const },
            ])
            .flat()
    }

    private defaultView(children: ChildrenLike) {
        if (!this.typeDoc?.name) {
            this.router.log({
                severity: 'Error',
                category: "Undefined type's name",
                message: { typeDoc: this.typeDoc, parent: this.parent },
            })
        }
        return {
            tag: 'div' as const,
            class: 'd-flex align-items-center',
            innerText: this.typeDoc?.name,
            children,
        }
    }
}

export class LinkedTypeView implements VirtualDOM<'div'> {
    public readonly path: string
    public readonly name: string
    public readonly router: Router
    public readonly configuration: Configuration
    public readonly tag = 'div'
    public readonly class = 'd-flex align-items-center'
    public readonly children: ChildrenLike

    constructor(params: {
        name: string
        path: string
        configuration: Configuration
        router: Router
        withChildren: AnyVirtualDOM[]
    }) {
        Object.assign(this, params)
        const path = this.path?.startsWith('youwol')
            ? `/references/${this.path.split('.').slice(0, -2).join('/')}.${
                  this.path.split('.').slice(-2)[0]
              }.${this.path.split('.').slice(-2)[1]}`
            : this.configuration.externalTypes[this.path]
        const isExternal = !this.path?.startsWith('youwol') && path
        if (!path) {
            this.router.log({
                severity: 'Warning',
                category: 'Unlinked type',
                message: this.path,
            })
        }
        this.children = path
            ? [
                  {
                      tag: 'a' as const,
                      class: 'd-flex align-items-center',
                      innerText: this.name,
                      href: path,
                      target: isExternal ? '_blank' : '',
                      onclick: (e) => {
                          if (!isExternal) {
                              e.preventDefault()
                              this.router.navigateTo({ path })
                          }
                      },
                  },
                  ...params.withChildren,
              ]
            : [
                  {
                      tag: 'div' as const,
                      class: 'd-flex align-items-center',
                      innerText: this.name,
                      children: params.withChildren,
                  },
              ]
    }
}
