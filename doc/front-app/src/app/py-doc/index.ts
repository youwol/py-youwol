import { PyYouwolClient } from '@youwol/local-youwol-client'
import { raiseHTTPErrors } from '@youwol/http-primitives'
import { map } from 'rxjs'
import { PyModuleView } from './module.view'
import { Router, Views } from '@youwol/mkdocs-ts'
import { AnyVirtualDOM } from '@youwol/rx-vdom'

export interface Configuration {
    decoratorView: ({ path }: { path: string }) => AnyVirtualDOM | undefined
    externalTypes: { [k: string]: string }
    codeUrl: (path: string, startLine: number) => string
}

export const pyYwReferenceDoc = ({
    modulePath,
    router,
}: {
    modulePath: string
    router: Router
}) => {
    const tocConvertor = (heading: HTMLHeadingElement): AnyVirtualDOM => {
        const classes = heading.firstChild
            ? (heading.firstChild as HTMLElement).classList?.value
            : ''

        return {
            tag: 'div' as const,
            innerText: heading.firstChild['innerText'],
            class: `${classes} fv-hover-text-focus`,
        }
    }
    return client.queryDocumentation({ path: modulePath }).pipe(
        raiseHTTPErrors(),
        map((moduleDoc) => {
            return {
                children:
                    moduleDoc.childrenModules?.length > 0
                        ? moduleDoc.childrenModules.map((m) => ({
                              name: m.name,
                              leaf: m.isLeaf,
                          }))
                        : [],
                html: async () =>
                    new PyModuleView({ moduleDoc, router, configuration }),
                tableOfContent: (d) =>
                    Views.tocView({ ...d, domConvertor: tocConvertor }),
            }
        }),
    )
}
