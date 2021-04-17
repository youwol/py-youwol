

## Description

The <a href="https://www.youwol.com/">YouWol</a> local full-stack environment.

This environment provides:
- a local version of the YouWol platform
- a developer environment to extend the platform (npm packages, backends, frontends)

What will come in the near future:
- the ability to synchronize local resources from and to the deployed platform

>The purpose of this full-stack environment is to provide a painless experience for developers who want to contribute to the 
>platform, in particular in terms of flexibility regarding the integration with developers' favorite stacks.
>Also the environment, while running in a browser, is completely 'locally sand-boxed' and there is no need
>of internet connection (besides the steps requiring installation of dependencies).

## Requirements

*   Tested on python *3.6.8* and *3.6.9*, should work on any 3.6.x with x>8. 
    YouWol is **not working** on python 3.7 to 3.9 for now 
*   We (strongly) recommend using one of the latest version of Google Chrome browser (e.g. >= 89). 
    Some features used by YouWol are available only on the latest releases of the major browsers, 
    also we did not have the time to thoroughly test the platform with other browsers than Chrome for now.

The YouWol environment can be completed by installing *pipelines*, 
those may require additional installation (e.g. *node*, *gcc*, etc); we refer the reader to their documentation.

## Installation

A good practice is to create a python virtual environment to host the *YouWol* python dependencies and to not 
affect your global python installation. 
You can also go with a global installation by running **pip install youwol** and proceed through the 
'Starting YouWol' section.

Create a folder in which you plan to organize your YouWol related works (referred as *youwol_folder* in what follows). 
Then create and activate a virtual environment (feel free to pick any name instead *youwol_venv*, in what follows
the name of the virtual env is referred as *youwol_venv*): 
-   For **Mac** and **Linux**:
```bash
python3.6 -m venv .youwol_venv
source .youwol_venv/bin/activate
```
-   For **Windows**

The installation hase been tested on python3.6.8, installed 
from <a href='https://www.python.org/downloads/release/python-368/'> here </a>

```bash
c:\Python368\python -m venv  .youwol_venv
.youwol_venv\Scripts\activate.bat
```

Then download and install *YouWol*:
```bash
pip install youwol
```

### Installation issues

Some common issues are listed at the end of this page, you may find a 
solution there if you encounter a problem during the installation.


### Installation test

From the created folder run youwol: ```youwol```

Try to navigate to:
-    the [dashboard](http://localhost:2000/ui/dashboard-developer/)
-    the [workspace](http://localhost:2000/ui/workspace-explorer/)

Test **Flux** with a simple project (note you won't be able to save changes):
-    [simple test](localhost:2000/ui/flux-builder/?uri=%7B%22name%22%3A%22new%20flux-project%22%2C%22description%22%3A%22%22%2C%22runnerRendering%22%3A%7B%22layout%22%3A%22%3Cdiv%20id%3D%5C%22in19%5C%22%3E%3Cdiv%20id%3D%5C%22i1yi%5C%22%3E%3Cdiv%20id%3D%5C%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3Cdiv%20id%3D%5C%22i8kh%5C%22%3E%3Cdiv%20id%3D%5C%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%5C%22%20class%3D%5C%22flux-element%5C%22%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%3C%2Fdiv%3E%22%2C%22style%22%3A%22*%20%7B%20box-sizing%3A%20border-box%3B%20%7D%20body%20%7Bmargin%3A%200%3B%7D%23in19%7Bdisplay%3Aflex%3Bwidth%3A100%25%3Bheight%3A100%25%3Bpadding%3A5px%3B%7D%23i1yi%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23i8kh%7Bmin-width%3A50px%3Bwidth%3A100%25%3B%7D%23Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%7Bheight%3A100%25%3Bwidth%3A100%25%3B%7D%23Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%7Bheight%3A100%25%3Bwidth%3A100%25%3B%7D%22%7D%2C%22builderRendering%22%3A%7B%22descriptionsBoxes%22%3A%5B%5D%2C%22modulesView%22%3A%5B%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22xWorld%22%3A-72.92934841579867%2C%22yWorld%22%3A316.16163465711804%7D%2C%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22xWorld%22%3A157.0706515842014%2C%22yWorld%22%3A350.6060791015625%7D%2C%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22xWorld%22%3A428.1817626953125%2C%22yWorld%22%3A337.2727457682292%7D%2C%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22xWorld%22%3A755.5555555555554%2C%22yWorld%22%3A315.3535630967882%7D%5D%2C%22connectionsView%22%3A%5B%5D%7D%2C%22requirements%22%3A%7B%22fluxComponents%22%3A%5B%5D%2C%22fluxPacks%22%3A%5B%22%40youwol%2Fflux-files%22%2C%22%40youwol%2Fflux-code-mirror%22%5D%2C%22libraries%22%3A%7B%22%40youwol%2Fflux-files%22%3A%220.0.3%22%2C%22%40youwol%2Fcdn-client%22%3A%220.0.3%22%2C%22%40youwol%2Fflux-view%22%3A%220.0.6%22%2C%22%40youwol%2Fflux-core%22%3A%220.0.7%22%2C%22%40youwol%2Ffv-button%22%3A%220.0.3%22%2C%22%40youwol%2Ffv-tree%22%3A%220.0.3%22%2C%22rxjs%22%3A%226.5.5%22%2C%22%40youwol%2Ffv-group%22%3A%220.0.3%22%2C%22lodash%22%3A%224.17.15%22%2C%22reflect-metadata%22%3A%220.1.13%22%2C%22%40youwol%2Fflux-code-mirror%22%3A%220.0.3%22%2C%22codemirror%22%3A%225.52.0%22%7D%2C%22loadingGraph%22%3A%7B%22graphType%22%3A%22sequential-v1%22%2C%22lock%22%3A%5B%7B%22name%22%3A%22%40youwol%2Fflux-files%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWZpbGVz%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22flux-pack%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fcdn-client%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9jZG4tY2xpZW50%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-view%22%2C%22version%22%3A%220.0.6%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-core%22%2C%22version%22%3A%220.0.7%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWNvcmU%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-button%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1idXR0b24%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-tree%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi10cmVl%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22rxjs%22%2C%22version%22%3A%226.5.5%22%2C%22id%22%3A%22cnhqcw%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Ffv-group%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22library%22%7D%2C%7B%22name%22%3A%22lodash%22%2C%22version%22%3A%224.17.15%22%2C%22id%22%3A%22bG9kYXNo%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22reflect-metadata%22%2C%22version%22%3A%220.1.13%22%2C%22id%22%3A%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22core_library%22%7D%2C%7B%22name%22%3A%22%40youwol%2Fflux-code-mirror%22%2C%22version%22%3A%220.0.3%22%2C%22id%22%3A%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%22%2C%22namespace%22%3A%22youwol%22%2C%22type%22%3A%22flux-pack%22%7D%2C%7B%22name%22%3A%22codemirror%22%2C%22version%22%3A%225.52.0%22%2C%22id%22%3A%22Y29kZW1pcnJvcg%3D%3D%22%2C%22namespace%22%3A%22%22%2C%22type%22%3A%22library%22%7D%5D%2C%22definition%22%3A%5B%5B%5B%22QHlvdXdvbC9jZG4tY2xpZW50%22%2C%22QHlvdXdvbC9jZG4tY2xpZW50%2F0.0.3%2Fdist%2F%40youwol%2Fcdn-client.js%22%5D%2C%5B%22cnhqcw%3D%3D%22%2C%22cnhqcw%3D%3D%2F6.5.5%2Frxjs.umd.min.js%22%5D%2C%5B%22bG9kYXNo%22%2C%22bG9kYXNo%2F4.17.15%2Flodash.min.js%22%5D%2C%5B%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%22%2C%22cmVmbGVjdC1tZXRhZGF0YQ%3D%3D%2F0.1.13%2Freflect-metadata.min.js%22%5D%2C%5B%22Y29kZW1pcnJvcg%3D%3D%22%2C%22Y29kZW1pcnJvcg%3D%3D%2F5.52.0%2Fcodemirror.min.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LXZpZXc%3D%22%2C%22QHlvdXdvbC9mbHV4LXZpZXc%3D%2F0.0.6%2Fdist%2F%40youwol%2Fflux-view.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LWNvcmU%3D%22%2C%22QHlvdXdvbC9mbHV4LWNvcmU%3D%2F0.0.7%2Fdist%2F%40youwol%2Fflux-core.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mdi1idXR0b24%3D%22%2C%22QHlvdXdvbC9mdi1idXR0b24%3D%2F0.0.3%2Fdist%2F%40youwol%2Ffv-button.js%22%5D%2C%5B%22QHlvdXdvbC9mdi10cmVl%22%2C%22QHlvdXdvbC9mdi10cmVl%2F0.0.3%2Fdist%2F%40youwol%2Ffv-tree.js%22%5D%2C%5B%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%22%2C%22QHlvdXdvbC9mdi1ncm91cA%3D%3D%2F0.0.3%2Fdist%2F%40youwol%2Ffv-group.js%22%5D%2C%5B%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%22%2C%22QHlvdXdvbC9mbHV4LWNvZGUtbWlycm9y%2F0.0.3%2Fdist%2F%40youwol%2Fflux-code-mirror.js%22%5D%5D%2C%5B%5B%22QHlvdXdvbC9mbHV4LWZpbGVz%22%2C%22QHlvdXdvbC9mbHV4LWZpbGVz%2F0.0.3%2Fdist%2F%40youwol%2Fflux-files.js%22%5D%5D%5D%7D%7D%2C%22workflow%22%3A%7B%22modules%22%3A%5B%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Explorer%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Explorer%22%2C%22description%22%3A%22This%20module%20allows%20to%20explore%20files%20and%20data%20in%20your%20workspace%22%2C%22data%22%3A%7B%22selectionEmit%22%3A%22single%20file%20only%22%7D%7D%7D%2C%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22factoryId%22%3A%7B%22module%22%3A%22LocalDrive%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Local%20Drive%22%2C%22description%22%3A%22A%20module%20to%20connect%20to%20a%20local%20folder%20of%20the%20computer%20for%20fetching%2Fbrowsing%20files.%22%2C%22data%22%3A%7B%22driveId%22%3A%22local-drive%22%2C%22driveName%22%3A%22local-drive%22%7D%7D%7D%2C%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Editor%22%2C%22pack%22%3A%22%40youwol%2Fflux-code-mirror%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Editor%22%2C%22description%22%3A%22Editor%22%2C%22data%22%3A%7B%22content%22%3A%22%5Cn%2F*%20This%20is%20the%20default%20content%20of%20the%20CodeMirror%20editor.%5CnYou%20can%20change%20it%20either%3A%5Cn%20%20%20%20%20*%20by%20updating%20(statically)%20the%20'content'%20property%20%5Cnof%20the%20module's%20configuration.%5Cn%20%20%20%20%20*%20by%20updating%20(dynamically)%20the%20'content'%20property%20%5Cnof%20the%20module's%20configuration%20using%20an%20adaptor.%5Cn*%2F%5Cnfunction%20foo()%7B%5Cn%20%20%20%20return%20'foo'%5Cn%7D%5Cn%22%2C%22mode%22%3A%22javascript%22%2C%22theme%22%3A%22eclipse%22%2C%22lineNumbers%22%3Atrue%7D%7D%7D%2C%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22factoryId%22%3A%7B%22module%22%3A%22Reader%22%2C%22pack%22%3A%22%40youwol%2Fflux-files%22%7D%2C%22configuration%22%3A%7B%22title%22%3A%22Reader%22%2C%22description%22%3A%22This%20module%20is%20used%20to%20read%20the%20content%20of%20the%20file%22%2C%22data%22%3A%7B%22mode%22%3A%22text%22%2C%22%22%3A%22Reader%22%7D%7D%7D%5D%2C%22connections%22%3A%5B%7B%22end%22%3A%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22slotId%22%3A%22drive%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22slotId%22%3A%22drive%22%7D%7D%2C%7B%22end%22%3A%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22slotId%22%3A%22file%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22slotId%22%3A%22selection%22%7D%7D%2C%7B%22end%22%3A%7B%22moduleId%22%3A%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%2C%22slotId%22%3A%22input%22%7D%2C%22start%22%3A%7B%22moduleId%22%3A%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22slotId%22%3A%22read%22%7D%2C%22adaptor%22%3A%7B%22adaptorId%22%3A%227945ebb6-1941-4707-9f47-59e69a9e327e%22%2C%22mappingFunction%22%3A%22%5Cnreturn%20(%7Bdata%2Cconfiguration%2Ccontext%7D)%20%3D%3E%20(%7B%5Cn%20%20%20%20data%3A%20data%2C%5Cn%20%20%20%20context%3A%7B%7D%2C%5Cn%20%20%20%20configuration%3A%20%7Bcontent%3A%20data.content%7D%5Cn%7D)%22%7D%7D%5D%2C%22plugins%22%3A%5B%5D%2C%22rootLayerTree%22%3A%7B%22layerId%22%3A%22rootLayer%22%2C%22moduleIds%22%3A%5B%22Explorer_a4276cdd-d33e-4dde-a4a6-1d1c9a09ce37%22%2C%22Reader_1abd900d-efcc-4366-9ac1-325339add87e%22%2C%22LocalDrive_b7a96c5d-57a5-4b1f-a5ad-9d8fc8626a5d%22%2C%22Editor_03044fa1-cab1-4e4e-88d7-56444c01fb9a%22%5D%2C%22title%22%3A%22rootLayer%22%2C%22children%22%3A%5B%5D%7D%7D%7D):
     accept the notification from your browser and select a text file from your computer

Try to create a new flux-pack:
-    from the [dashboard](http://localhost:2000/ui/dashboard-developer/) create a new package
-    select 'flux-pack', give a name & description, and validate
-    you should see an 'Install' invite in the dashboard, proceed with it
-    once done, *build, test, publish* using the &#8594; button

Create a new project from the [workspace](http://localhost:2000/ui/workspace-explorer/):
-    navigate into **private** from the explorer on the right
-    if needed create a drive and a folder using right click menu
-    right click on the folder and select **new app**, then click **construct**
-    right click on the top *builder-panel*, select *import module(s)*
-    expand the explorer and navigate in **private/default-drive** and expand your package
-    select 'a simple module' and click 'OK'

From there you look at the documentation: select the module, from the *settings panel*
you can access its documentation.

Some links:
-    [flux-core documentation](http://localhost:2000/api/assets-gateway/raw/package/QHlvdXdvbC9mbHV4LWNvcmU=/latest/dist/docs/modules/core_concepts.html)

## Starting YouWol

### First start

From the *youwol_folder* created during the installation, run in a shell:
```bash
youwol
```
Proceed with the creation of a new workspace with default settings when asked.
After a few seconds, you should be invited to visit either:
-   the <a href="http://localhost:2000/ui/assets-browser-ui/">assets browser ui</a>: this is your YouWol workspace from
    which you can organize your assets and contruct/run your *flux-apps* (flux refers to the low code solution developed 
    by youwol)
-   the <a href="http://localhost:2000/ui/local-dashboard/">local dashboard</a>: this is the dashboard that helps
    developers to create new resources to expose in your workspace (npm packages, frontends, backends)

Looking at the content of the *youwol_folder* you can see that a bunch of resources has been created.
You can have a look at the file 'yw_config.py' that describes the configuration (more on that in the dedicated section). 

> One efficient approach to work with the configuration file and with YouWol python files is to use 
> <a href='https://www.jetbrains.com/fr-fr/pycharm/'>PyCharm</a> along with the plugin 
> <a href='https://pydantic-docs.helpmanual.io/pycharm_plugin/'>pydantic</a>. 
> You can open the *youwol_folder* using PyCharm and set the python interpreter to .youwol_venv/bin/python3.6.

### Latter execution

When running youwol you need to provide the path to an initial configuration file 
(if not, the creation of a default workspace is prompted as illustrated above). 
You can provide the path to an existing configuration by either:
-  using the *--conf* command line option: 
   
```youwol --conf=path/to/your/config-file.py```
-  executing ```youwol``` from a folder that already contains a configuration file called 'yw_config.py'.

Note that you can switch to other configuration file when youwol is running 
from the <a href="http://localhost:2000/ui/local-dashboard/">local dashboard</a>.

Also, more options are available when starting youwol, try ```youwol --help``` to get them listed.

## Creating applications using Flux - YouWol low code solution -

From the <a href="http://localhost:2000/ui/assets-browser-ui/">assets browser ui</a> you can browse the folder
```/youwol-users/assets/flux-app-samples/hello-flux``` and launch the application 
using the <button>construct</button> button. 
The application provides insights on how the low code solution *flux* is working, and drives you through an
interactive training plan. 
An extended documentation of *flux* is on his way.

You can also start scratching your new application by using a right click on a folder of the assets-browser and
select <button>new app</button>.


## Extending the platform

Extending the platform is based on the concept of pipeline. 
A pipeline gather the definition on how to build/test/deploy assets (for now packages, frontends, backends) in 
a particular way using some particular toolchain. 
A pipeline provides the ability to the local platform to create and run/deploy resources in a couple of clicks
from the <a href="http://localhost:2000/ui/local-dashboard/">local dashboard</a> (e.g. visit for
instance *My computer > Packages > <button>new package</button>*).

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

You can use pipelines created by others on <a herf="https://pypi.org/">PyPi</a>.
We recommend to the developers prefixing the pipeline name by 'yw_pipeline_' to facilitate searching them in the repository.

Once installed (ideally in the virtual env you have created for youwol - see installation section),
you can include them in your configuration file (see explanation in the default 'yw_config.py' file).

### Creating your own pipelines

A good place to start is looking at the implementation of the pipelines that come with the installation of *YouWol*, 
some efforts have been dedicated to their documentation.
One way of accessing this documentation is to *ctrl+click* on the name of a pipeline of your configuration
file (at the top, in the imports section) using your favorite IDE (your IDE should open the associated 
source file). 


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
