
## Scope 

This section presents the fundamentals of consuming dependencies, either frontend libraries or backend services.
It is a rapid overview, more information on each topic can be found in the section [webPM](../how-to/webpm.md).

## Prerequisite

Beside the last example - involving backend installation - the examples does not require anything else than
a web-browser: you can copy/paste them in an `index.html` file opened by your favorite browser.
Regarding the last example, it should be executed with youwol started.

## Javascript modules

Let's start by installing a javascript module to create the view of the application:

<div id="load-screen"></div>

```custom-view
const src = `
return async ({debug}) => {
    const { marked } = await webpm.install({
        modules:['marked#^4.2.3 as marked'],
        displayLoadingScreen: true
    })
    const output = '# Pi computation'
    const div = document.createElement('div')
    div.classList.add('fv-bg-primary', 'h-100')
    div.innerHTML = marked.parse(output)
    debug('view', div)
}`

return async ({webpm}) => { 
    const {grapes} = await webpm.install({modules:['@youwol/grapes-coding-playgrounds#^0.2.0 as grapes']})
    console.log(grapes)
    console.log(webpm)
    const view = await grapes.jsPlaygroundView({
        loadingScreenContainer: document.getElementById("load-screen"),
        testSrc:'return async ()=>{}',
        returnType:'vdom',
        src
    })
    console.log('view', view)
    return view
}
```


```javascript hl_lines="1-4"
const { marked } = await webpm.install({
    modules:['marked#^5.52.0 as marked'],
    displayLoadingScreen: true
})
const output = `# Pi computation`

document.body.innerHTML = marked.parse(output)
```

The code highlighted proceed to the installation of the dependencies.
The javascript module <a href='https://www.npmjs.com/package/marked' >marked</a> is installed using the latest 
version compatible with `^5.52.0`. 
When installing modules, eventual direct and indirect dependencies are also downloaded and linked appropriately, 
here again using the latest compatible version available.
The process account for the actual runtime hosted by the browser: preventing useless downloads while ensuring 
coexistence of multiple library's versions if needed.

The remaining code is about creating an output using the markdown module just installed.


## Python 

It is possible to install python runtime and python modules, for instance to use `numpy` add the following line:

```javascript hl_lines="3 6-13 16-17"
const { marked } = await webpm.install({
    modules:['marked#^5.52.0 as marked'],
    python:['numpy'],
    displayLoadingScreen: true
})
const src = `
import numpy as np
n = 1000
data = np.random.uniform(-0.5, 0.5, size=(n, 2))
norms = np.linalg.norm(data, axis=1)
len(np.argwhere(norms<0.5)) / n * 4
`
const pi = webpm.python.runPython(src)

const output = `# Pi computation

The approximation computed from python in the browser is ${pi}
`

document.body.innerHTML = marked.parse(output)
```

In the example:

*  the `numpy` python module is requested; requesting python modules initialize the python runtime, later accessible 
using `webpm.python`.
*  in the next block an approximation of PI is computed using a Monte Carlo method
*  the value is the displayed in the output


## Backends
<div id="a"></div>

```javascript hl_lines="4 16 21-22"
const { marked, pyBackend } = await webpm.install({
    modules:['marked#^4.2.3 as marked'],
    python:['numpy'],
    backends:['@youwol/python-numpy#^1.0.0 as pyBackend'],
    displayLoadingScreen: true
})
const src = `
import numpy as np
n = 1000
data = np.random.uniform(-0.5, 0.5, size=(n, 2))
norms = np.linalg.norm(data, axis=1)
len(np.argwhere(norms<0.5)) / n * 4
`
const pi = webpm.python.runPython(src)

const piBackend = await pyBackend.fetch('/interpret',{ src})

const output = `# Pi computation

The approximation computed from python in the browser is ${pi}.

The approximation computed from python in the backend is ${piBackend}.
`
document.body.innerHTML = marked.parse(output)
```