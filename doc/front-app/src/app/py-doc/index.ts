import { map, Observable } from 'rxjs'
import { PyModuleView } from './module.view'
import { Navigation, Router, Views } from '@youwol/mkdocs-ts'
import { AnyVirtualDOM } from '@youwol/rx-vdom'
import { configuration } from './configurations'
import { Routers, PyYouwolClient } from '@youwol/local-youwol-client'
import { request$, raiseHTTPErrors } from '@youwol/http-primitives'
import { setup } from '../../auto-generated'

const tableOfContent = Views.tocView
export type ServingMode = 'dynamic' | 'static'

function fetchModuleDoc({
    modulePath,
    servingMode,
}: {
    modulePath: string
    servingMode: ServingMode
}): Observable<Routers.System.DocModuleResponse> {
    const dynamicMode =
        servingMode === 'dynamic' &&
        document.location.origin.startsWith('http://localhost')
    const basePath = `/api/assets-gateway/raw/package/${setup.assetId}/${setup.version}/assets/api`
    const client = new PyYouwolClient().admin.system
    const assetPath = `${basePath}/${modulePath}.json`
    const from$ = dynamicMode
        ? client.queryDocumentation({ path: modulePath })
        : request$<Routers.System.DocModuleResponse>(new Request(assetPath))
    return from$.pipe(raiseHTTPErrors())
}

export const pyDocNav: (servingMode: ServingMode) => Navigation = (
    servingMode: ServingMode,
) => ({
    name: 'youwol',
    tableOfContent,
    html: ({ router }) =>
        fetchModuleDoc({ modulePath: 'youwol', servingMode }).pipe(
            map((moduleDoc: Routers.System.DocModuleResponse) => {
                return new PyModuleView({ moduleDoc, router, configuration })
            }),
        ),
    '...': ({ path, router }: { path: string; router: Router }) =>
        pyYwReferenceDoc({ modulePath: path, servingMode, router }),
})
export const pyYwReferenceDoc = ({
    modulePath,
    router,
    servingMode,
}: {
    modulePath: string
    router: Router
    servingMode: ServingMode
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
    if (modulePath === '') {
        modulePath = 'youwol'
    }
    return fetchModuleDoc({ modulePath, servingMode }).pipe(
        map((moduleDoc) => {
            return {
                children:
                    moduleDoc.childrenModules?.length > 0
                        ? moduleDoc.childrenModules.map((m) => ({
                              name: m.name,
                              leaf: m.isLeaf,
                              id: m.name,
                          }))
                        : [],
                html: () =>
                    new PyModuleView({ moduleDoc, router, configuration }),
                tableOfContent: (d: { html: HTMLElement; router: Router }) =>
                    Views.tocView({ ...d, domConvertor: tocConvertor }),
            }
        }),
    )
}
