
## Scope

This tutorial described how to publish locally a simple javascript + HTML application.

The all setup is done automatically, such that there is no need to worry about configurations
(2 files of about 10 lines of code). Should you want to publish your own application from scratch, you can refer to this
[How-To guide](../how-to/projects/raw-application.md).



## Prerequisites:

This tutorial is using a predefined configuration, please load it by:

*  opening a terminal and running youwol using
```shell
youwol --conf=@py_youwol_tour/js_app.py --port=2003 --force-restart=true
```
*  after started, reload the page [here](http://localhost:2000/applications/py-youwol-doc/latest/tutorials/new-app/)


## The developer portal

The application embedded above is the **Developer Portal**. When youwol is started, it can be accessed from
`http://localhost:2000/`, assuming `2000` is the http port used (default port).

The main objective of the application is to provide to users facilities to create libraries, applications, 
or backends. Its main navigation is proposed from the left panel, more information on its usage can be found from
this [How-To guide](../how-to/dev-portal-usage.md), for the time being a couple of its feature will be exposed in what 
follows.

## Configuration file

The actual configuration file used by youwol is displayed in the tab
<i class="rounded border fv-bg-background-alt fv-text-primary align-items-center px-1" style="font-style: normal">Environment <i class="fas fa-globe"></i></i>
under the section
<i class="rounded border fv-bg-background fv-text-primary align-items-center px-1" style="font-style: normal"><i class="fas fa-file-alt"></i> Config. file</i>.

It is the central place to configure the youwol server. Here, the important points regarding the configuration are:

*  `finder=RecursiveProjectsFinder(...)`: defines a strategy that look-up for new projects as a background task.
   Any time a folder representing a project is added as a child of `projects_folder` it will be automatically detected.
   More info regarding projects detection can be found in this [How-To guide](../how-to/configuration/workspace.md).
*  `endPoints=CustomEndPoints(...)`: defines a new command as a REST API end point to clone the project 
   <a href="https://github.com/youwol/todo-app-ts"  target="_blank">@youwol/todo-app-js</a> from GitHUB. 
   More info regarding customization can be found in this [How-To guide](../how-to/configuration/customize.md).


## Clone the github project


From the *dev.portal*:

*  select the <i class="rounded border fv-bg-background-alt fv-text-primary align-items-center px-1" style="font-style: normal">Environment <i class="fas fa-globe"></i></i> tab
*  select the command **git-clone-todo-app-js** in the section <i class="rounded border fv-bg-background fv-text-primary align-items-center px-1" style="font-style: normal"><i class="fas fa-play"></i> Commands</i>
*  execute it using the button <i class=" fv-bg-secondary rounded border fv-text-primary" style="font-style: normal; width:fit-content"><i class="fas fa-play  px-2"></i></i>


## Publish the project


Start by opening the project from the developer portal:

*  select the tab <i class="rounded border fv-bg-background-alt fv-text-primary align-items-center px-1" style="font-style: normal">Projects <i class="fas fa-file-code"></i></i>,
*  select `@youwol/todo-app-js` in the section <i class="rounded border fv-bg-background fv-text-primary align-items-center px-1" style="font-style: normal"><i class="fas fa-list-alt"></i>All projects</i>

The flowchart displayed on the screen represents the project's pipeline, it is defined in a file `yw_pipeline` in 
the project's folder. It is most of the time very simple as it re-use pipeline implementation shared by the community.
In this particular case, the 
<a href="https://github.com/youwol/todo-app-js/blob/master/.yw_pipeline/yw_pipeline.py" target="_blank"> file</a> 
uses the 'native' `pipeline-raw-app` from youwol package. 

Proceed by running the three connected steps in the following order:

*  **init**: This step installs the necessary dependencies.
*  **build**: This step creates the `dist` artifact, in this simple case it only gathers the files `index.html`, `style.css` and `package.json`.
*  **cdn-local**: This step publishes the artifacts created in previous steps (in this case, only `dist`) to the 
local CDN database.


> 🎉 Your application can be executed by navigating to this  <a href='http://localhost:2000/applications/@youwol/todo-app-js/latest' target='_blank'>URL</a>

## Going further

The youwol configuration and the project's pipeline has been directly provided in this tutorial,
this [How-To guide](../how-to/projects/raw-application.md) describe how to publish your own project from scratch.

The [next tutorial](shared-dependencies.md) explores an interesting case that allow to publish a 'collaborative' application,
being able to link the application dynamically to allow transparent upgrade from the work on others 
on its dependencies.

