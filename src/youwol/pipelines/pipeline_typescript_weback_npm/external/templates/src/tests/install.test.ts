import { install } from '@youwol/webpm-client'
import './mock-requests'
import { cleanDocument, installPackages, setupPyYouwolBackend } from './common'
import { setup } from '../auto-generated'
import * as originalPackage from '{{name}}'

beforeAll(async () => {
    // If the package does requires dependencies from webPM, turn off the option 'localOnly'
    setupPyYouwolBackend({ port: 2001, localOnly: true })
    // Be sure to have run the 'cdn-local' step of the pipeline through dev-portal before running the test.
    // It generates the 'cdn.zip' files used below
    await installPackages(['../../cdn.zip'])
})

beforeEach(() => {
    cleanDocument()
    // need @youwol/cdn-client#2.1.1 to be enabled
    // State.clear()
})

test('install {{name}}', async () => {
    const notExported : string[] = [
        // Provide the name of the symbols that are not exported for a good reason + give the reason
    ];
    await install({
        modules: [`${setup.name}#${setup.version}`],
    })
    expect(document.scripts).toHaveLength(1)
    const webpmPackage = globalThis[`${setup.name}_APIv${setup.apiVersion}`]
    expect(webpmPackage).toBeTruthy()
    const originalProperties = Object.keys(originalPackage)
    const notFound = originalProperties.filter((p) => !webpmPackage[p])
    if (notFound.length > 0) {
        console.warn(
            `${notFound.length} properties out of ${originalProperties.length} of lodash are not found:`,
            notFound
        );
    }
    const missing = notFound.filter((p) => !notExported.includes(p));
    if (missing.length > 0) {
        console.error(
            `${missing.length} properties out of ${originalProperties.length} of lodash are not found but required`,
            missing
        );
    }
    expect(missing).toHaveLength(0)
})
