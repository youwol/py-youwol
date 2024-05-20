
const runTimeDependencies = {
    "externals": {
        "@youwol/http-primitives": "^0.2.3",
        "@youwol/local-youwol-client": "^0.2.6",
        "@youwol/mkdocs-ts": "^0.3.2",
        "@youwol/rx-tab-views": "^0.3.0",
        "@youwol/rx-vdom": "^1.0.1",
        "@youwol/webpm-client": "^3.0.0",
        "rxjs": "^7.5.6"
    },
    "includedInBundle": {}
}
const externals = {
    "@youwol/http-primitives": "window['@youwol/http-primitives_APIv02']",
    "@youwol/local-youwol-client": "window['@youwol/local-youwol-client_APIv02']",
    "@youwol/mkdocs-ts": "window['@youwol/mkdocs-ts_APIv03']",
    "@youwol/rx-tab-views": "window['@youwol/rx-tab-views_APIv03']",
    "@youwol/rx-vdom": "window['@youwol/rx-vdom_APIv1']",
    "@youwol/webpm-client": "window['@youwol/webpm-client_APIv3']",
    "rxjs": "window['rxjs_APIv7']"
}
const exportedSymbols = {
    "@youwol/http-primitives": {
        "apiKey": "02",
        "exportedSymbol": "@youwol/http-primitives"
    },
    "@youwol/local-youwol-client": {
        "apiKey": "02",
        "exportedSymbol": "@youwol/local-youwol-client"
    },
    "@youwol/mkdocs-ts": {
        "apiKey": "03",
        "exportedSymbol": "@youwol/mkdocs-ts"
    },
    "@youwol/rx-tab-views": {
        "apiKey": "03",
        "exportedSymbol": "@youwol/rx-tab-views"
    },
    "@youwol/rx-vdom": {
        "apiKey": "1",
        "exportedSymbol": "@youwol/rx-vdom"
    },
    "@youwol/webpm-client": {
        "apiKey": "3",
        "exportedSymbol": "@youwol/webpm-client"
    },
    "rxjs": {
        "apiKey": "7",
        "exportedSymbol": "rxjs"
    }
}

const mainEntry : {entryFile: string,loadDependencies:string[]} = {
    "entryFile": "./main.ts",
    "loadDependencies": [
        "@youwol/mkdocs-ts",
        "@youwol/rx-vdom",
        "@youwol/webpm-client",
        "rxjs",
        "@youwol/local-youwol-client",
        "@youwol/rx-tab-views",
        "@youwol/http-primitives"
    ]
}

const secondaryEntries : {[k:string]:{entryFile: string, name: string, loadDependencies:string[]}}= {}

const entries = {
     '@youwol/py-youwol-doc': './main.ts',
    ...Object.values(secondaryEntries).reduce( (acc,e) => ({...acc, [`@youwol/py-youwol-doc/${e.name}`]:e.entryFile}), {})
}
export const setup = {
    name:'@youwol/py-youwol-doc',
        assetId:'QHlvdXdvbC9weS15b3V3b2wtZG9j',
    version:'0.1.10-wip',
    shortDescription:"Py-youwol documentation application",
    developerDocumentation:'https://platform.youwol.com/applications/@youwol/cdn-explorer/latest?package=@youwol/py-youwol-doc&tab=doc',
    npmPackage:'https://www.npmjs.com/package/@youwol/py-youwol-doc',
    sourceGithub:'https://github.com/youwol/py-youwol-doc',
    userGuide:'https://l.youwol.com/doc/@youwol/py-youwol-doc',
    apiVersion:'01',
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
            return window[`@youwol/py-youwol-doc_APIv01`]
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
            `@youwol/py-youwol-doc#0.1.10-wip~dist/@youwol/py-youwol-doc/${entry.name}.js`
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
            return window[`@youwol/py-youwol-doc/${entry.name}_APIv01`]
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
