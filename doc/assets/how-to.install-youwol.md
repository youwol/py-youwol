# Installation

## Requirements

Py-YouWol support the Python versions {PYTHON_VERSIONS}.

## Option 1: Installing with pipx

To install Py-YouWol using pipx, you need to have Python and pipx installed on your machine. Once you have those, just issue the following command:

`pipx install youwol`

If you want, you can install from the sources instead of using Pypi package - the `editable` flag has the same effect as for `pip`, see [setuptools documentation](https://setuptools.pypa.io/en/latest/userguide/development_mode.html):

`pipx install <path-to-py-youwol-src> --editable`

- where `path-to-py-youwol-src` is the path of the py-youwol folder (e.g. cloned from <a target='_blank' href='https://github.com/youwol/py-youwol'> here </a>)

Once installed, you can run the application from anywhere with `youwol`.

## Option 2: Installing from pip

To install Py-YouWol using pip, you need to have Python and pip installed on your machine. Once you have those, you can follow these steps:

1. Create a virtual environment (recommended) using python3: `python3 -m venv venv`
2. Activate the virtual environment: `source venv/bin/activate` (on Linux/Mac) or `venv\Scripts\activate` (on Windows)
3. Install the package: `pip install youwol`

Each time you want to run the application, you need to activate the virtual environment like in step 2. Once that virtual environment is activated, run the application with `youwol`.

## Option 3: Installing from GitHub

If you prefer to install Py-YouWol from the source code, you can find it on GitHub at the following
[link](https://github.com/youwol/py-youwol).

To install from source code, you will need to have Git and Python installed on your machine. Once you have those, you can follow these steps:

1. Clone the repository from GitHub: `git clone https://github.com/youwol/py-youwol`
2. Navigate to the project directory: `cd py-youwol`
3. Create a virtual environment (recommended) using python3: `python3 -m venv venv`
4. Activate the virtual environment: `source venv/bin/activate` (on Linux/Mac) or `venv\Scripts\activate` (on Windows)
5. Install the required packages: `pip install -r requirements.txt`
6. Reference the `src` folder of the repository in your python paths (e.g. `export PYTHONPATH=path/to/folder/py-youwol/src`)
7. Run the application, for instance from the root folder: `python src/youwol/main.py`
