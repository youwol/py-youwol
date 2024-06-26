import { fromMarkdown, Views } from '@youwol/mkdocs-ts'
import { setup } from '../auto-generated'
import { youwolInfo } from '../auto-generated-toml'
import { formatPythonVersions } from './utils'
import { pyDocNav } from './py-doc'

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

export const navigation = {
    name: 'YouWol',
    tableOfContent,
    html: fromMd({
        file: 'index.md',
        placeholders: {
            '{YW_VERSION}': youwolInfo.version,
            '{PYTHON_RECOMMENDED}': youwolInfo.pythons.slice(-1)[0],
        },
    }),
    '/tutorials': {
        name: 'Tutorials',
        tableOfContent,
        html: fromMd({ file: 'tutorials.md' }),
        // '/dyn-deps': {
        //     name: 'Dynamic dependencies',
        //     tableOfContent,
        //     html: fromMd({ file: 'tutorials.dynamic-dependencies.md' }),
        // },
        // '/raw-app': {
        //     name: "Publish a 'raw' app.",
        //     tableOfContent,
        //     html: fromMd({ file: 'tutorials.publish-raw-app.md' }),
        // },
    },
    '/how-to': {
        name: 'How-To Guides',
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
    '/gallery': {
        name: 'Gallery',
        tableOfContent,
        html: fromMd({ file: 'gallery.md' }),
    },
    '/references': {
        name: 'References',
        tableOfContent,
        html: fromMd({ file: 'references.md' }),
        '/youwol': pyDocNav('static'),
    },
    '/change-log': {
        name: 'Change Log',
        tableOfContent,
        html: fromMd({ file: 'CHANGELOG.md' }),
    },
}
