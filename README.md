

## Description

The <a href="https://www.youwol.com/">YouWol</a> local full-stack environment (YouWol FSE).

This environment provides:
- a local version of the YouWol platform
- a developer environment to extend the platform (npm packages, backends, frontends)

>The purpose of this full-stack environment is to provide a painless experience for developers who want to contribute to the 
>platform, in particular in terms of flexibility regarding the integration with developers' favorite stacks.
>Also the environment, while running in a browser, is completely 'locally sand-boxed' and there is no need
>of internet connection (besides the steps requiring installation of dependencies).
<div style="max-width:100%; overflow:auto">
    <div style="display:flex; width:250%; margin:auto">
        <figure style="text-align: center; font-style: italic;">
            <img src="https://raw.githubusercontent.com/youwol/dashboard-developer/master/images/screenshots/dashboard.png" 
             alt="" >
            <figcaption >Dashboard view: develop and publish your code. Integrate your favorite stack using pipelines.
            </figcaption>
        </figure>
        <figure style="text-align: center; font-style: italic;">
            <img src="https://raw.githubusercontent.com/youwol/flux-builder/master/images/screenshots/overall-view.png" 
             alt="" >
            <figcaption >Flux builder: low code solution of YouWol. Build your application using drag & drop.</figcaption>
        </figure>
        <figure style="text-align: center; font-style: italic;">
            <img src="https://raw.githubusercontent.com/youwol/workspace-explorer/master/images/screenshots/workspace-explorer.png" 
             alt="" >
            <figcaption >Workspace explorer: browse & organize your assets. Define accessibility.</figcaption>
        </figure>
    </div>
</div>

## Requirements


*   Tested (lightly) on python *3.6*, *3.7*, *3.8* and *3.6.9*, we recommend *3.9.5*
    as it is the python's version we use in YouWol
*   We (strongly) recommend using one of the latest version of Google Chrome browser (e.g. >= 89). 
    Some features used by YouWol are available only on the latest releases of the major browsers, 
    also we did not have the time to thoroughly test the platform with other browsers than Chrome for now.
*   To build a flux-pack ensure a node version > v14.x 
The YouWol FSE environment can be completed by installing *pipelines*, 
those may require additional installation (e.g. *node*, *gcc*, etc.); we refer the reader to their documentation.

## Installation from pypi

A good practice is to create a python virtual environment to host the *YouWol* python dependencies and to not 
affect your global python installation. 
You can also go with a global installation by running **pip install youwol** and proceed through the 
'Starting YouWol' section.

Create a folder in which you plan to organize your YouWol related works (referred as *youwol_folder* in what follows). 
Then create and activate a virtual environment (feel free to pick any name instead *youwol_venv*, in what follows
the name of the virtual env is referred as *youwol_venv*): 
-   For **Mac** and **Linux**:
```bash
python3.9 -m venv .youwol_venv
source .youwol_venv/bin/activate
```
-   For **Windows**

The installation hase been tested on python3.9.5, installed 
from <a href='https://www.python.org/downloads/release/python-395/'> here </a>

```bash
c:\Python395\python -m venv  .youwol_venv
.youwol_venv\Scripts\activate.bat
```

Then download and install *YouWol*:
```bash
pip install youwol
```

## Installation from source

Clone the gitHub repository, e.g. for master:
```bash
git clone https://github.com/youwol/py-youwol.git
```
Go through the installation steps described in the previous section, 
but replace:
```bash
pip install youwol
```
by (from the cloned folder py-youwol):
```bash
python setup.py install
```

To update the installation with respect to new sources:
-    activate the created virtual environment
-    from py-youwol folder:
```bash
git pull
python setup.py install
```


## Installation issues

Some common issues are listed at the end of this page, you may find a 
solution there if you encounter a problem during the installation.


### First steps

From the created folder run youwol:

```bash
youwol
```
Proceed with the creation of a new workspace with default settings when asked.

> The links in what follows assume you've started the environment on the port 2000 - the default.
> In case you can't use it, you can provide a '--port XXX' option to the command line, following
> links will need to be corrected in your browser (just replace '2000' by 'XXX').

#### Landing pages

Two landing pages comes with the installation:
-    the [dashboard](http://localhost:2000/ui/dashboard-developer/):
     it gathers information about current developments, 
     this is where you will easily create packages/backends/frontends 
-    the [workspace-explorer](http://localhost:2000/ui/workspace-explorer/):
     the workspace-explorer is your YouWol assets manager, this is where you can 
     browse your assets, edit metadata, give permission, upload data, create flux applications, and more. 

#### Flux builder

*Flux builder* is the low code application builder of YouWol, you can test it by following this 
[link](localhost:2000/ui/flux-builder/?uri=%7B%22name%22%3A%22new%20flux-project%22%2C%22description%22%3A%22%22%2C%22runnerRendering%22%3A%7B%22layout%22%3A%22%3Cdiv%20id%3D%5C%22in19%5C%22%3E%3Cdiv%20id%3D%5C%22i1yi%5C%22%3E%3Cdiv%20id%3D%5C%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3Cdiv%20id%3D%5C%22i8kh%5C%22%3E%3Cdiv%20id%3D%5C%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%22%2C%22style%22%3A%22*%20%7B%20box-sizing%3A%20border-box%3B%20%7D%20body%20%7Bmargin%3A%200%3B%7D%23in19%7Bdisplay%3Aflex%3Bwidth%3A100%25%3Bheight%3A100%25%3Bpadding%3A5px%3B%7D%23i1yi%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23i8kh%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%7Bheight%3A100%25%3Bwidth%3A100%25%3B%7D%23Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%7Bheight%3A100%25%3Bwidth%3A100%25%3B%7D%22%7D%2C%22builderRendering%22%3A%7B%22descriptionsBoxes%22%3A%5B%5D%2C%22modulesView%22%3A%5B%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22xWorld%22%3A-72.92934841579867%2C%22yWorld%22%3A316.16163465711804%7D%2C%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22xWorld%22%3A157.0706515842014%2C%22yWorld%22%3A350.6060791015625%7D%2C%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22xWorld%22%3A428.1817626953125%2C%22yWorld%22%3A337.2727457682292%7D%2C%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22xWorld%22%3A755.5555555555554%2C%22yWorld%22%3A315.3535630967882%7D%5D%2C%22connectionsView%22%3A%5B%5D%7D%2C%22requirements%22%3A%7B%22fluxComponents%22%3A%5B%5D%2C%22fluxPacks%22%3A%5B%22%40youwol%2Fflux-files%22%2C%22%40youwol%2Fflux-code-mirror%22%5D%2C%22libraries%22%3A%7B%22%40youwol%2Fflux-files%22%3A%220.0.3%22%2C%22%40youwol%2Fcdn-client%22%3A%220.0.3%22%2C%22%40youwol%2Fflux-view%22%3A%220.0.6%22%2C%22%40youwol%2Fflux-core%22%3A%220.0.7%22%2C%22%40youwol%2Ffv-button%22%3A%220.0.3%22%2C%22%40youwol%2Ffv-tree%22%3A%220.0.3%22%2C%22rxjs%22%3A%226.5.5%22%2C%22%40youwol%2Ffv-group%22%3A%220.0.3%22%2C%22lodash%22%3A%224.17.15%22%2C%22reflect-metadata%22%3A%220.1.13%22%2C%22%40youwol%2Fflux-code-mirror%22%3A%220.0.3%22%2C%22codemirror%22%3A%225.52.0%22%7D%2C%22loadingGraph%22%3A%7B%22graphType%22%3A%22sequential-v1%22%2C%22lock%22%3A%5B%7B%22name%22%3A%22%40youwol%2Fflux-files%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWZpbGVz%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22flux-pack%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fcdn-client%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9jZG4tY2xpZW50%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-view%22%2C%22version%22%3A%220.0.6%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-core%22%2C%22version%22%3A%220.0.7%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWNvcmU%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-button%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1idXR0b24%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-tree%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi10cmVl%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22rxjs%22%2C%22version%22%3A%226.5.5%22%2C%22id%22%3A%22cnhqcw%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-group%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22lodash%22%2C%22version%22%3A%224.17.15%22%2C%22id%22%3A%22bG9kYXNo%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22reflect-metadata%22%2C%22version%22%3A%220.1.13%22%2C%22id%22%3A%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-code-mirror%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22flux-pack%22%7D%2C%7B%22name%22%3A%22codemirror%22%2C%22version%22%3A%225.52.0%22%2C%22id%22%3A%22Y29kZW1pcnJvcg%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22library%22%7D%5D%2C%22definition%22%3A%5B%5B%5B%22QHlvdXdvbC9jZG4tY2xpZW50%22%2C%22QHlvdXdvbC9jZG4tY2xpZW50%2F0.0.3%2Fdist%2F%40youwol%2Fcdn-client.js%22%5D%2C%5B%22cnhqcw%3D%3D%22%2C%22cnhqcw%3D%3D%2F6.5.5%2Frxjs.umd.min.js%22%5D%2C%5B%22bG9kYXNo%22%2C%22bG9kYXNo%2F4.17.15%2Flodash.min.js%22%5D%2C%5B%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%2C%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%2F0.1.13%2Freflect-metadata.min.js%22%5D%2C%5B%22Y29kZW1pcnJvcg%3D%3D%22%2C%22Y29kZW1pcnJvcg%3D%3D%2F5.52.0%2Fcodemirror.min.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%2C%22QHlvdXdvbC9mbHV4LXZpZXc%3D%2F0.0.6%2Fdist%2F%40youwol%2Fflux-view.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LWNvcmU%3D%22%2C%22QHlvdXdvbC9mbHV4LWNvcmU%3D%2F0.0.7%2Fdist%2F%40youwol%2Fflux-core.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mdi1idXR0b24%3D%22%2C%22QHlvdXdvbC9mdi1idXR0b24%3D%2F0.0.3%2Fdist%2F%40youwol%2Ffv-button.js%22%5D%2C%5B%22QHlvdXdvbC9mdi10cmVl%22%2C%22QHlvdXdvbC9mdi10cmVl%2F0.0.3%2Fdist%2F%40youwol%2Ffv-tree.js%22%5D%2C%5B%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%2C%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%2F0.0.3%2Fdist%2F%40youwol%2Ffv-group.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%22%2C%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%2F0.0.3%2Fdist%2F%40youwol%2Fflux-code-mirror.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LWZpbGVz%22%2C%22QHlvdXdvbC9mbHV4LWZpbGVz%2F0.0.3%2Fdist%2F%40youwol%2Fflux-files.js%22%5D%5D%5D%7D%7D%2C%22workflow%22%3A%7B%22modules%22%3A%5B%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Explorer%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Explorer%22%2C%22description%22%3A%22This%20module%20allows%20to%20explore%20files%20and%20data%20in%20your%20workspace%22%2C%22data%22%3A%7B%22selectionEmit%22%3A%22single%20file%20only%22%7D%7D%7D%2C%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22factoryId%22%3A%7B%22module%22%3A%22LocalDrive%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Local%20Drive%22%2C%22description%22%3A%22A%20module%20to%20connect%20to%20a%20local%20folder%20of%20the%20computer%20for%20fetching%2Fbrowsing%20files.%22%2C%22data%22%3A%7B%22driveId%22%3A%22local-drive%22%2C%22driveName%22%3A%22local-drive%22%7D%7D%7D%2C%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Editor%22%2C%22pack%22%3A%22%40youwol%2Fflux-code-mirror%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Editor%22%2C%22description%22%3A%22Editor%22%2C%22data%22%3A%7B%22content%22%3A%22%5Cn%2F*%20This%20is%20the%20default%20content%20of%20the%20CodeMirror%20editor.%5CnYou%20can%20change%20it%20either%3A%5Cn%20%20%20%20%20*%20by%20updating%20(statically)%20the%20'content'%20property%20%5Cnof%20the%20module's%20configuration.%5Cn%20%20%20%20%20*%20by%20updating%20(dynamically)%20the%20'content'%20property%20%5Cnof%20the%20module's%20configuration%20using%20an%20adaptor.%5Cn*%2F%5Cnfunction%20foo()%7B%5Cn%20%20%20%20return%20'foo'%5Cn%7D%5Cn%22%2C%22mode%22%3A%22javascript%22%2C%22theme%22%3A%22eclipse%22%2C%22lineNumbers%22%3Atrue%7D%7D%7D%2C%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Reader%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Reader%22%2C%22description%22%3A%22This%20module%20is%20used%20to%20read%20the%20content%20of%20the%20file%22%2C%22data%22%3A%7B%22mode%22%3A%22text%22%2C%22%22%3A%22Reader%22%7D%7D%7D%5D%2C%22connections%22%3A%5B%7B%22end%22%3A%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22slotId%22%3A%22drive%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22slotId%22%3A%22drive%22%7D%7D%2C%7B%22end%22%3A%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22slotId%22%3A%22file%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22slotId%22%3A%22selection%22%7D%7D%2C%7B%22end%22%3A%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22slotId%22%3A%22input%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22slotId%22%3A%22read%22%7D%2C%22adaptor%22%3A%7B%22adaptorId%22%3A%227945ebb6-1941-4707-9f47-59e69a9e327e%22%2C%22mappingFunction%22%3A%22%5Cnreturn%20(%7Bdata%2Cconfiguration%2Ccontext%7D)%20%3D%3E%20(%7B%5Cn%20%20%20%20data%3A%20data%2C%5Cn%20%20%20%20context%3A%7B%7D%2C%5Cn%20%20%20%20configuration%3A%20%7Bcontent%3A%20data.content%7D%5Cn%7D)%22%7D%7D%5D%2C%22plugins%22%3A%5B%5D%2C%22rootLayerTree%22%3A%7B%22layerId%22%3A%22rootLayer%22%2C%22moduleIds%22%3A%5B%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%5D%2C%22title%22%3A%22rootLayer%22%2C%22children%22%3A%5B%5D%7D%7D%7D):
 
The project is a very simple files browser + code-editor kind of application. 
It allows to browse your local computer and display & edit text files.
Because it needs to access your local filesystem, you need to accept the authorization request from your browser
while picking a root directory to explore.

> Note that because the project is loaded from an uri (there is no actual project saved somewhere),
> you won't be able to save your change.

#### Flux-pack

*Flux-packs* are npm packages defining modules for **Flux**. The installation of YouWol comes
with a **flux-pack pipeline**: it formalises how to *create / build / test / publish* them, in this case
typescript and webpack are used behind the wood. 
There exist several types of pipeline, they formalise how to work with some kind of assets 
in a specific way (i.e. with a specific tools stack). 
They can be installed and published from/to pypi. 

Let's have a try with the creation of a new **Flux-pack**:
-    from the [dashboard](http://localhost:2000/ui/dashboard-developer/) create a new package:
     **My Computer** > **Packages** > **new package**
-    select the pipeline **flux-pack** in the dropdown menu at the top of the modal, 
     give it a name & description, and validate (name can include namespace, e.g. '@myspace/xxx' )
-    you should see an **Install** invite in the dashboard, proceed with it
-    once done, *build, test, publish* using the icon &#8594; (in the column **Actions**); 
     if everything went fine your newly created **flux-pack** is ready to be used in a flux application.

> Although you don't need internet connection to work with the YouWol FSE usually, it becomes required
> when you need to proceed with installation steps fetching dependencies.

#### Build a flux application

From the [workspace-explorer](http://localhost:2000/ui/workspace-explorer/), create a new project:
-    navigate into **private** from the explorer on the left
-    if needed, create a drive and a folder using right click menus
     > The workspace-explorer is based on a folders/files explorer just like a personal computer.
     > It can be ambiguous to distinguish drive from folder, they serve about the same purpose: grouping
     > entities together. For now, you can consider a drive just as a top-level folder.
-    right-click on the folder and select **new app**, then click **construct**, **flux-builder** application 
     should start
     
Import the module exposed in the previously built **flux-pack**
-    right-click on the top *builder-panel* and select *import module(s)*
-    expand the explorer and navigate in **private/default-drive**, expand your package
-    select 'a simple module' and click 'OK'

You can now use the package you've just build, you can access its documentation to learn more about
the module & flux (accessible when you select the module in the *builder-panel* from the *settings panel*)

Should you want to dive deeper into the creation of modules for flux, you can have a first pass over the 
[flux-core documentation](http://localhost:2000/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/core_concepts.html).

## Configuration

YouWol FSE is based on a python configuration file: it describes the code-based assets you are working on
(npm-packages, front-ends, back-ends).

Looking at the content of the folder you used to start ```youwol``` you can see that a bunch of 
resources has been created. 
It includes the configuration file 'yw_config.py': the one that comes by default with YouWol FSE install.

> One efficient approach to work with the configuration file and with YouWol python files is to use 
> <a href='https://www.jetbrains.com/fr-fr/pycharm/'>PyCharm</a> along with the plugin 
> <a href='https://pydantic-docs.helpmanual.io/pycharm_plugin/'>pydantic</a>. 
> You can open the folder you used to start ```youwol``` using PyCharm and set the 
> python interpreter to .youwol_venv/bin/python3.6. - if .youwol_venv is the name of your python's virtual environment.

When running ```youwol``` you need to provide a way to retrieve the configuration file: 
-  using the *--conf* command line option: 
   
```youwol --conf=path/to/your/config-file.py```
-  executing ```youwol``` from a folder that already contains a configuration file called 'yw_config.py'.

If neither of the two above options is used, the creation of a default workspace is prompted. 

Note that you can switch to other configuration file when youwol is running 
from the <a href="http://localhost:2000/ui/local-dashboard/">developer's dashboard</a>.

Also, more options are available when starting youwol, try ```youwol --help``` to get them listed.


## Extending the platform

Extending the platform is based on the concept of pipeline. 
A pipeline formalises how to build/test/deploy assets (for now packages, frontends, backends) using 
a specific stack.


The installation of YouWol comes with 4 different pipelines:
- **simple-pack** (category 'Packages'): 
  provides the automation on a solution to create npm package using typescript and webpack.
- **flux-pack** (category 'Packages'):
  provides the automation on a solution to create npm package using typescript and webpack
  with a skeleton that provides example on how to create modules for *Flux*.
- **scratch-html** (category 'Front Ends'):
  provides the automation on a solution to create simple HTML/javascript/CSS front ends.
- **fast-api** (category 'Back Ends):
  provides the automation on a solution to create a python backend 
  using the <a href="https://fastapi.tiangolo.com/">FastApi</a> framework.
  
When you create a new asset you can visit the README.md file in the associated folder 
(new assets are located by default under *youwol_folder/workspace/...* )

### Installing new pipelines

You can use pipelines created by others on <a href="https://pypi.org/">PyPi</a>.

Once installed (ideally in the virtual env you have created for youwol - see installation section),
you can include them in your configuration file (see explanation in the default 'yw_config.py' file).

### Creating your own pipelines

A good place to start is looking at the implementation of the pipelines that come with the installation of *YouWol*, 
some efforts have been dedicated to their documentation. You can adapt and publish them on 
<a href="https://pypi.org/">PyPi</a>.

## install issues


### Ubuntu
#### 'fatal error: Python.h: No such file or directory'

```
multidict/_multidict.c:1:10: fatal error: Python.h: No such file or directory
#include "Python.h"
              ^~~~~~~~~~
    compilation terminated.
```
Solution: you need to run: 
```
sudo apt-get install python3.x-dev
```  
where **x** is the python version 
you are using to run ```youwol```
