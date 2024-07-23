import { fromMarkdown, installCodeApiModule, Views } from '@youwol/mkdocs-ts'
import { setup } from '../auto-generated'
import { youwolInfo } from '../auto-generated-toml'
import { formatPythonVersions } from './utils'

const tableOfContent = Views.tocView
function fromMd({
    file,
    placeholders,
}: {
    file: string
    placeholders?: { [_: string]: string }
}) {
    return fromMarkdown({
        url: `/api/assets-gateway/raw/package/${setup.assetId}/${setup.version}/assets/${file}`,
        placeholders,
    })
}

const CodeApiModule = await installCodeApiModule()

const configuration = {
    ...CodeApiModule.configurationPython,
    codeUrl: ({ path, startLine }: { path: string; startLine: number }) => {
        const baseUrl = 'https://github.com/youwol/py-youwol/tree'
        const target = setup.version.endsWith('-wip')
            ? 'main'
            : `v${setup.version}`
        return `${baseUrl}/${target}/src/youwol/${path}#L${startLine}`
    },
}
export const navigation = {
    name: 'Py-YouWol',
    decoration: {
        icon: { tag: 'div' as const, class: 'fas fa-home mr-2' },
    },
    tableOfContent,
    html: fromMd({
        file: 'index.md',
        placeholders: {
            '{YW_VERSION}': youwolInfo.version,
            '{PYTHON_RECOMMENDED}': youwolInfo.pythons.slice(-1)[0],
        },
    }),
    '/how-to': {
        name: 'How-To',
        decoration: {
            icon: { tag: 'div' as const, class: 'fas fa-list-ul mr-2' },
        },
        tableOfContent,
        html: fromMd({ file: 'how-to.md' }),
        '/install-youwol': {
            name: 'Installation',
            tableOfContent,
            html: fromMd({
                file: 'how-to.install-youwol.md',
                placeholders: {
                    '{PYTHON_VERSIONS}': formatPythonVersions(),
                },
            }),
        },
        '/start-youwol': {
            name: 'Start youwol',
            tableOfContent,
            html: fromMd({ file: 'how-to.start-youwol.md' }),
        },
    },
    '/api': CodeApiModule.codeApiEntryNode({
        name: 'API',
        decoration: {
            icon: { tag: 'div', class: 'fas fa-code mr-2' },
        },
        entryModule: 'youwol',
        docBasePath: '../assets/api',
        configuration: configuration,
    }),
    '/change-log': {
        name: 'Change Log',
        decoration: {
            icon: { tag: 'div' as const, class: 'fas fa-bookmark mr-2' },
        },
        tableOfContent,
        html: fromMd({ file: 'CHANGELOG.md' }),
    },
}
