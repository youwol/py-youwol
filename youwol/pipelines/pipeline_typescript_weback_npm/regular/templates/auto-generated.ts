
const runTimeDependencies = '{{runTimeDependencies}}'
const externals = '{{externals}}'
const exportedSymbols = '{{exportedSymbols}}'
export const setup = {
    name:'{{name}}',
        assetId:'{{assetId}}',
    version:'{{version}}',
    shortDescription:"{{shortDescription}}",
    developerDocumentation:'{{developerDocumentation}}',
    npmPackage:'{{npmPackage}}',
    sourceGithub:'{{sourceGithub}}',
    userGuide:'{{userGuide}}',
    apiVersion:'{{apiVersion}}',
    runTimeDependencies,
    externals,
    exportedSymbols,
    getDependencySymbolExported: (module:string) => {
        return `${exportedSymbols[module].exportedSymbol}_APIv${exportedSymbols[module].apiKey}`
    }
}
