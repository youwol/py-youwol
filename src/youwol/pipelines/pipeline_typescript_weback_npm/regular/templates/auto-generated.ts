
const runTimeDependencies = '{{runTimeDependencies}}'
const externals = '{{externals}}'
const exportedSymbols = '{{exportedSymbols}}'

const mainEntry : {entryFile: string,loadDependencies:string[]} = '{{mainEntry}}'

const secondaryEntries : {[k:string]:{entryFile: string, name: string, loadDependencies:string[]}}= '{{secondaryEntries}}'

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
    secondaryEntries,
    getDependencySymbolExported: (module:string) => {
        return `${exportedSymbols[module].exportedSymbol}_APIv${exportedSymbols[module].apiKey}`
    },

    installMainModule: ({cdnClient, installParameters}:{
        cdnClient:{install:(unknown) => Promise<WindowOrWorkerGlobalScope>},
        installParameters?
    }) => {
        const parameters = installParameters || {}
        const scripts = parameters.scripts || []
        const modules = [
            ...(parameters.modules || []),
            ...mainEntry.loadDependencies.map( d => `${d}#${runTimeDependencies.externals[d]}`)
        ]
        return cdnClient.install({
            ...parameters,
            modules,
            scripts,
        }).then(() => {
            return window[`{{name}}_APIv{{apiVersion}}`]
        })
    },
    installAuxiliaryModule: ({name, cdnClient, installParameters}:{
        name: string,
        cdnClient:{install:(unknown) => Promise<WindowOrWorkerGlobalScope>},
        installParameters?
    }) => {
        const entry = secondaryEntries[name]
        if(!entry){
            throw Error(`Can not find the secondary entry '${name}'. Referenced in template.py?`)
        }
        const parameters = installParameters || {}
        const scripts = [
            ...(parameters.scripts || []),
            `{{name}}#{{version}}~dist/{{name}}/${entry.name}.js`
        ]
        const modules = [
            ...(parameters.modules || []),
            ...entry.loadDependencies.map( d => `${d}#${runTimeDependencies.externals[d]}`)
        ]
        return cdnClient.install({
            ...parameters,
            modules,
            scripts,
        }).then(() => {
            return window[`{{name}}/${entry.name}_APIv{{apiVersion}}`]
        })
    },
    getCdnDependencies(name?: string){
        if(name && !secondaryEntries[name]){
            throw Error(`Can not find the secondary entry '${name}'. Referenced in template.py?`)
        }
        const deps = name ? secondaryEntries[name].loadDependencies : mainEntry.loadDependencies

        return deps.map( d => `${d}#${runTimeDependencies.externals[d]}`)
    }
}
