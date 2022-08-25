

## Description

The <a href="https://www.youwol.com/">YouWol</a> local full-stack environment (YouWol FSE).

This environment provides:
- a local version of the YouWol platform
- a developer environment to extend the platform (npm packages, backends, frontends). 
Developers are able to integrate their favorite tool-chains.
- while mostly 'locally sand-boxed', an internet connection is required for:
  - authentication
  - installation of missing assets. Installation are lazy: they are triggered when required, 
  it can be libraries, application, data, etc

## Requirements

*   We recommend using python *3.9* as it is the python's version we use in YouWol
*   We (strongly) recommend using one of the latest version of Google Chrome browser (e.g. >= 100). 
    Some features used by YouWol are available only on the latest releases of the major browsers, 
    also we did not have the time to thoroughly test the platform with other browsers than Chrome for now.

## Installation
### From pypi

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

### From source

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


Some common issues are listed at the end of this page, you may find a
solution there if you encounter a problem during the installation.


### Developer's installation (IntelliJ / PyCharm)

Recommended plugins in IntelliJ:
*  python
*  pydantic

Clone the gitHub repository, e.g. for master:
```bash
git clone https://github.com/youwol/py-youwol.git
```

Create a virtual environment using python3.9, in IntelliJ:
*  *Ctrl+Alt+Shift+S*
* SDK -> add -> new python SDK
* select python3.9 as base interpreter

In the created virtual environment, add a `youwol.pth` file in `lib64/python3.9/site-packages`
and set its content to the absolute path of the folder `py-youwol`.

Create an alias command for 'youwol' starting youwol. E.g. in linux system:

`alias youwol=”{PATH_TO_VENV}/bin/python3.9 {PATH_TO_PY_YOUWOL}/youwol/main.py”`
Where:
*  PATH_TO_VENV is the absolute path to the python's virtual environment created
*  PATH_TO_PY_YOUWOL is the absolute path to the py-youwol folder checked ou from git
Save it to your `~/.bashrc` file.

### Installation issues

Some common issues are listed at the end of this page, you may find a 
solution there if you encounter a problem during the installation.


## Getting started

Start youwol, in a terminal:

```bash
youwol
```
Proceed with initialization with default settings and open the link displayed in the terminal in a browser.

From the applications launcher menu (top-right icon in the top-banner), two of them can be visited first:
*  developer portal: the application to help create and publish asset to the platform
*  explorer: file system of youwol

You can find the complete guide to py-youwol and how to create assets [here](https://l.youwol.com/doc/py-youwol).

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
