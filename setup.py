import glob
import os
from pathlib import Path
from setuptools import setup, find_packages

# The directory containing this file
here = Path(__file__).parent

# The text of the README file
README = (Path(__file__).parent / "README.md").read_text()

data_files = []
for pipeline in ['fastapi', 'flux_pack', 'library_webpack_ts', 'scribble_html']:
    for root, dirs, files in os.walk(f"youwol/pipelines/{pipeline}/files_template", topdown=False):
        data_files.append((root, [f'{root}/{f}' for f in files]))


setup(
    name='youwol',
    python_requires='~=3.6',
    version='0.0.2',
    description="Local YouWol environment",
    author="Guillaume Reinisch",
    author_email="reinisch.gui@youwol.com",
    long_description=README,
    long_description_content_type="text/markdown",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        ],
    packages=find_packages(include=[
        'youwol',
        'youwol_utils',
        'youwol_utils.**',
        'youwol_data',
        'youwol.**'
        ]),
    data_files=data_files,
    package_data={
        'youwol_data': ['databases.zip'],
        'youwol.services.fronts.dashboard_developer': ['*.html', '*.js', '*.css', '*.map'],
        'youwol.services.fronts.workspace_explorer': ['*.html', '*.js', '*.css', '*.map'],
        'youwol.services.fronts.flux_builder': ['*.html', '*.js', '*.css', '*.map'],
        'youwol.services.fronts.flux_runner': ['*.html', '*.js', '*.css', '*.map']
        },
    include_package_data=True,
    install_requires=[
        "cowpy==1.1.0",
        "aiohttp==3.7.3",
        "fastapi==0.63.0",
        "uvicorn==0.13.3",
        "python-multipart==0.0.5",
        "aiohttp==3.7.3",
        "async==0.6.2",
        "websockets==8.1",
        "watchgod==0.7",
        "aiofiles==0.6.0",
        "async_generator==1.10",
        "pillow==8.1.0"
        ],
    entry_points={
        'console_scripts': ['youwol=youwol.main:main']
        }
    )