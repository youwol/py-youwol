
const runTimeDependencies = '{{runTimeDependencies}}'
const externals = '{{externals}}'
const exportedSymbols = '{{exportedSymbols}}'

const entries = {
    '{{name}}': '{{main-entry-file}}',
}
export const setup = {
    name:'{{name}}',
    assetId:'{{assetId}}',
    version:'{{version}}',
    shortDescription:"{{shortDescription}}",
    apiVersion:'{{apiVersion}}',
    runTimeDependencies,
    externals,
    exportedSymbols,
    entries,
}

