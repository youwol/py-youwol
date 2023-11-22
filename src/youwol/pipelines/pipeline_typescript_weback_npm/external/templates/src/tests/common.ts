import { AssetsGateway, ExplorerBackend } from '@youwol/http-clients'
import {
    LocalYouwol,
    raiseHTTPErrors,
    RootRouter,
} from '@youwol/http-primitives'
import { readFileSync } from 'fs'
import path from 'path'
import { from } from 'rxjs'
import { mergeMap, reduce, take } from 'rxjs/operators'
import { Client, backendConfiguration } from '@youwol/webpm-client'

export function setupPyYouwolBackend({
    localOnly,
    port,
}: {
    localOnly: boolean
    port: number
}) {
    RootRouter.HostName = globalThis.youwolJestPresetGlobals.integrationUrl
    RootRouter.Headers = {
        'py-youwol-local-only': localOnly ? 'true' : 'false',
    }
    Client.BackendConfiguration = backendConfiguration({
        origin: { port },
        pathLoadingGraph:
            '/api/assets-gateway/cdn-backend/queries/loading-graph',
        pathResource: '/api/assets-gateway/raw/package',
    })
    Client.Headers = RootRouter.Headers
}
/**
 *
 * @param packages paths of 'cdn.zip' files from 'tests' directory
 */
export function installPackages(packages: string[]) {
    const assetsGtw = new AssetsGateway.AssetsGatewayClient()
    const pyYouwol = new LocalYouwol.Client()
    const obs = resetPyYouwolDbs$().pipe(
        mergeMap(() => {
            return pyYouwol.admin.environment.login$({
                body: {
                    authId: 'int_tests_yw-users@test-user',
                    envId: 'integration',
                },
            })
        }),
        mergeMap(() => assetsGtw.explorer.getDefaultUserDrive$()),
        raiseHTTPErrors(),
        mergeMap((resp: ExplorerBackend.GetDefaultDriveResponse) => {
            return from(
                packages.map((zipPath) => ({
                    folderId: resp.homeFolderId,
                    zip: zipPath,
                })),
            )
        }),
        mergeMap(({ folderId, zip }) => {
            const buffer = readFileSync(path.resolve(__dirname, zip))
            const arraybuffer = Uint8Array.from(buffer).buffer

            return assetsGtw.cdn
                .upload$({
                    queryParameters: { folderId },
                    body: { fileName: zip, blob: new Blob([arraybuffer]) },
                })
                .pipe(take(1))
        }),
        reduce((acc, e) => [...acc, e], []),
    )
    return new Promise((resolve) => {
        obs.subscribe((d) => resolve(d))
    })
}

export function resetPyYouwolDbs$() {
    return new LocalYouwol.Client().admin.customCommands.doGet$({
        name: 'reset',
    })
}

export function cleanDocument() {
    document.body.innerHTML = ''
    document.head.innerHTML = ''
}
