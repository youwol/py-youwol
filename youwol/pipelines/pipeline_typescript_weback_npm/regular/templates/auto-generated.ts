
const runTimeDependencies = '{{runTimeDependencies}}'
const externals = '{{externals}}'
const exportedSymbols = '{{exportedSymbols}}'

// eslint-disable-next-line @typescript-eslint/ban-types -- allow to allow no secondary entries
const mainEntry : Object = '{{mainEntry}}'

// eslint-disable-next-line @typescript-eslint/ban-types -- allow to allow no secondary entries
const secondaryEntries : Object = '{{secondaryEntries}}'
const entries = {
     '{{name}}': '{{main-entry-file}}',
    ...Object.values(secondaryEntries).reduce( (acc,e) => ({...acc, [`{{name}}/${e.name}`]:e.entryFile}), {})
}
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
    entries,
    getDependencySymbolExported: (module:string) => {
        return `${exportedSymbols[module].exportedSymbol}_APIv${exportedSymbols[module].apiKey}`
    },

    installMainModule: ({cdnClient, installParameters}:{cdnClient, installParameters?}) => {
        const parameters = installParameters || {}
        const scripts = parameters.scripts || []
        const modules = [
            ...(parameters.modules || []),
            ...mainEntry['loadDependencies'].map( d => `${d}#${runTimeDependencies.externals[d]}`)
        ]
        return cdnClient.install({
            ...parameters,
            modules,
            scripts,
        }).then(() => {
            return window[`{{name}}_APIv{{apiVersion}}`]
        })
    },
    installAuxiliaryModule: ({name, cdnClient, installParameters}:{name: string, cdnClient, installParameters?}) => {
        const entry = secondaryEntries[name]
        const parameters = installParameters || {}
        const scripts = [
            ...(parameters.scripts || []),
            `{{name}}#{{version}}~dist/{{name}}/${entry.name}.js`
        ]
        const modules = [
            ...(parameters.modules || []),
            ...entry.loadDependencies.map( d => `${d}#${runTimeDependencies.externals[d]}`)
        ]
        if(!entry){
            throw Error(`Can not find the secondary entry '${name}'. Referenced in template.py?`)
        }
        return cdnClient.install({
            ...parameters,
            modules,
            scripts,
        }).then(() => {
            return window[`{{name}}/${entry.name}_APIv{{apiVersion}}`]
        })
    }
}
