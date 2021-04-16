

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
